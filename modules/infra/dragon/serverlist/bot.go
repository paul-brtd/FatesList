package serverlist

import (
	"context"
	"dragon/common"
	"dragon/types"
	"strconv"
	"strings"
	"time"

	"github.com/bwmarrin/discordgo"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var (
	debug        bool                   = true
	iResponseMap map[string]*time.Timer = make(map[string]*time.Timer, 0) // Interaction response map to check if interaction has been responded to
)

func SetupSlash(discord *discordgo.Session) {
	cmdInit()

	// Add the slash commands
	for cmdName, v := range commands {
		if v.Disabled {
			continue
		}
		cmd := discordgo.ApplicationCommand{
			Name:        v.InternalName,
			Description: v.Description,
			Options:     v.SlashOptions,
		}
		log.Info("Loading slash command: ", cmdName)

		var server string

		if debug {
			server = common.StaffServer
		} else {
			server = ""
		}

		_, err := discord.ApplicationCommandCreate(discord.State.User.ID, server, &cmd)
		if err != nil {
			log.Fatal("Server: ", server, " - Cannot create command ", cmdName, " with description: ", cmd.Description, " due to error: ", err)
		}
	}
	log.Info("All slash commands loaded!")
}

func SlashHandler(
	ctx context.Context,
	discord *discordgo.Session,
	rdb *redis.Client,
	db *pgxpool.Pool,
	i *discordgo.InteractionCreate,
) {
	var appCmdData = i.ApplicationCommandData()

	var op string = commandNameCache[appCmdData.Name]

	if op == "" {
		return
	}

	if i.Interaction.Member == nil {
		sendIResponse(discord, i.Interaction, "This bot may only be used in a server!", true)
		return
	}

	cmd := commands[op]

	// Handle cooldown
	if cmd.Cooldown != types.CooldownNone {
		key := "cooldown-" + cmd.Cooldown.InternalName + "-" + i.Interaction.Member.User.ID
		cooldown, err := rdb.TTL(ctx, key).Result() // Format: cooldown-BUCKET-MOD
		if err == nil && cooldown.Seconds() > 0 {
			sendIResponse(discord, i.Interaction, "Please wait "+cooldown.String()+" before retrying this command!", true)
			return
		}
		rdb.Set(ctx, key, "0", time.Duration(cmd.Cooldown.Time)*time.Second)
	}

	check := checkPerms(discord, i.Interaction, cmd.Perm)
	if !check {
		return
	}

	slashContext := types.ServerListContext{
		Context:     ctx,
		Postgres:    db,
		Redis:       rdb,
		Discord:     discord,
		Interaction: i.Interaction,
	}

	res := cmd.Handler(slashContext)

	if res == "" {
		return
	}

	sendIResponse(discord, i.Interaction, res, true)
	delete(iResponseMap, i.Interaction.Token)
}

func checkPerms(discord *discordgo.Session, i *discordgo.Interaction, permNum int) bool {
	var perm int64
	var permStr string
	switch permNum {
	case 1:
		perm = discordgo.PermissionSendMessages
		permStr = "Send Messages"
	case 2:
		perm = discordgo.PermissionManageServer
		permStr = "Manage Server or Administrator"
	case 3:
		perm = discordgo.PermissionAdministrator
		permStr = "Administrator"
	default:
		perm = discordgo.PermissionAdministrator
		permStr = "Administrator"
	}
	if i.Member.Permissions&perm == 0 {
		sendIResponse(discord, i, "You need "+permStr+" in order to use this command", true)
		return false
	}

	if permNum >= 4 {
		ok, is_staff, perm := common.GetPerms(discord, context.Background(), i.Member.User.ID, float32(permNum+1))
		if ok != "" {
			sendIResponse(discord, i, "Something went wrong while verifying your identity!", true)
			return false
		}
		if !is_staff {
			sendIResponse(discord, i, "This operation requires perm: "+strconv.Itoa(int(permNum+1))+" but you only have perm number "+strconv.Itoa(int(perm))+".", true)
			return false
		}
	}
	return true
}

func sendIResponse(discord *discordgo.Session, i *discordgo.Interaction, content string, clean bool, largeContent ...string) {
	sendIResponseComplex(discord, i, content, clean, 0, largeContent)
}

func sendIResponseEphemeral(discord *discordgo.Session, i *discordgo.Interaction, content string, clean bool, largeContent ...string) {
	sendIResponseComplex(discord, i, content, clean, 1<<6, largeContent)
}

func sendIResponseComplex(discord *discordgo.Session, i *discordgo.Interaction, content string, clean bool, flags uint64, largeContent []string) {
	// Sends a response to a interaction using iResponseMap as followup if needed. If clean is set, iResponseMap is cleaned out
	var files []*discordgo.File
	for i, data := range largeContent {
		files = append(files, &discordgo.File{
			Name:        "output" + strconv.Itoa(i) + ".txt",
			ContentType: "application/octet-stream",
			Reader:      strings.NewReader(data),
		})
	}

	t, ok := iResponseMap[i.Token]
	if ok {
		_, err := discord.FollowupMessageCreate(discord.State.User.ID, i, true, &discordgo.WebhookParams{
			Content: content,
			Flags:   flags,
			Files:   files,
		})
		if err != nil {
			log.Error(err.Error())
		}
	} else {
		err := discord.InteractionRespond(i, &discordgo.InteractionResponse{
			Type: discordgo.InteractionResponseChannelMessageWithSource,
			Data: &discordgo.InteractionResponseData{
				Content: content,
				Flags:   flags,
				Files:   files,
			},
		})
		if err != nil {
			log.Error("An error has occurred in initial response: " + err.Error())
			discord.InteractionRespond(i, &discordgo.InteractionResponse{
				Type: discordgo.InteractionResponseDeferredChannelMessageWithSource,
			})
			sendIResponse(discord, i, "Something happened!\nError: "+err.Error(), false)
			return
		}
	}

	if clean {
		if ok && t != nil {
			t.Stop()
		}
		delete(iResponseMap, i.Token)
	} else {
		if !ok {
			iResponseMap[i.Token] = time.AfterFunc(15*time.Minute, func() {
				delete(iResponseMap, i.Token)
			})
		}
	}
}

func recovery() {
	err := recover()
	if err != nil {
		log.Error(err)
	}
}

func getArg(discord *discordgo.Session, i *discordgo.Interaction, name string, possibleLink bool) interface{} {
	// Gets an argument, if possibleLink is set, this will convert the possible link using common/converters.go if possible
	defer recovery()
	appCmdData := i.ApplicationCommandData()
	for _, v := range appCmdData.Options {
		if v.Name == name {
			if v.Type == discordgo.ApplicationCommandOptionString {
				sVal := strings.TrimSpace(v.StringValue())
				if possibleLink {
					return common.RenderPossibleLink(sVal)
				}
				return sVal
			} else if v.Type == discordgo.ApplicationCommandOptionInteger {
				return v.IntValue()
			} else if v.Type == discordgo.ApplicationCommandOptionBoolean {
				return v.BoolValue()
			} else if v.Type == discordgo.ApplicationCommandOptionUser {
				return v.UserValue(discord)
			}
		}
	}
	return nil
}
