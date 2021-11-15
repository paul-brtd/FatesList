package serverlist

import (
	"context"
	"dragon/common"
	"dragon/types"
	"time"

	"github.com/bwmarrin/discordgo"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var debug bool = true

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
		sendIResponse(discord, i.Interaction, "This bot may only be used in a server!")
		return
	}

	cmd := commands[op]

	// Handle cooldown
	if cmd.Cooldown != types.CooldownNone {
		key := "cooldown-" + cmd.Cooldown.InternalName + "-" + i.Interaction.Member.User.ID
		cooldown, err := rdb.TTL(ctx, key).Result() // Format: cooldown-BUCKET-MOD
		if err == nil && cooldown.Seconds() > 0 {
			sendIResponse(discord, i.Interaction, "Please wait "+cooldown.String()+" before retrying this command!")
			return
		}
		rdb.Set(ctx, key, "0", time.Duration(cmd.Cooldown.Time)*time.Second)
	}

	var perm int64
	var permStr string
	switch cmd.Perm {
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
	if i.Interaction.Member.Permissions&perm == 0 {
		sendIResponse(discord, i.Interaction, "You need "+permStr+" in order to use this command")
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
		sendIResponse(discord, i.Interaction, "This operation has completed successfully!")
		return
	}

	sendIResponse(discord, i.Interaction, res)
}

func sendIResponse(discord *discordgo.Session, i *discordgo.Interaction, content string) {
	discord.InteractionRespond(i, &discordgo.InteractionResponse{
		Type: discordgo.InteractionResponseChannelMessageWithSource,
		Data: &discordgo.InteractionResponseData{
			Content: content,
		},
	})
}

func recovery() {
	err := recover()
	log.Error(err)
}

func getArg(discord *discordgo.Session, i *discordgo.Interaction, name string, possibleLink bool) interface{} {
	// Gets an argument, if possibleLink is set, this will convert the possible link using common/converters.go if possible
	defer recovery()
	appCmdData := i.ApplicationCommandData()
	for _, v := range appCmdData.Options {
		if v.Name == name {
			if v.Type == discordgo.ApplicationCommandOptionString {
				if possibleLink {
					return common.RenderPossibleLink(v.StringValue())
				}
				return v.StringValue()
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
