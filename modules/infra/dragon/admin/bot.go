package admin

import (
	"context"
	"dragon/common"
	"dragon/types"
	"strconv"

	"github.com/bwmarrin/discordgo"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

// Prepend is complement to builtin append.
func Prepend[T any](items []T, item T) []T {
	return append([]T{item}, items...)
}

func SetupSlash(discord *discordgo.Session) {
	cmdInit()

	// Delete global commands
	cmds, err := discord.ApplicationCommands(discord.State.User.ID, "")
	if err != nil {
		log.Warn(err)
	}
	for _, cmd := range cmds {
		discord.ApplicationCommandDelete(discord.State.User.ID, "", cmd.ID)
	}

	// Add the slash commands

	botIdOption := discordgo.ApplicationCommandOption{
		Type:        discordgo.ApplicationCommandOptionUser,
		Name:        "bot",
		Description: "Bot (either ID or mention)",
		Required:    true,
	}
	for cmdName, v := range commands {
		if !v.SlashSupported {
			continue
		}
		if !v.SlashRaw {
			v.SlashOptions = Prepend(v.SlashOptions, &botIdOption)
		}
		cmd := discordgo.ApplicationCommand{
			Name:        v.InternalName,
			Description: v.Description,
			Options:     v.SlashOptions,
		}
		log.Info("Loading slash command: ", cmdName)
		_, err := discord.ApplicationCommandCreate(discord.State.User.ID, v.Server, &cmd)
		if err != nil {
			log.Fatal("Server: ", v.Server, " - Cannot create command ", cmdName, " with description: ", cmd.Description, " due to error: ", err)
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

	var botId string
	var op string = commandNameCache[appCmdData.Name]
	var reason string
	var extraContext string

	if op == "" {
		return
	}

	cmd := commands[op]

	// Get required name of context field/the name of the argument that should be treated as context
	var slashContext string

	if cmd.SlashContextField == "" {
		slashContext = "context"
	} else {
		slashContext = cmd.SlashContextField
	}

	// Get needed interaction options using loop
	for _, v := range appCmdData.Options {
		if v.Name == "bot" {
			botId = v.UserValue(discord).ID
		} else if v.Name == "reason" {
			reason = common.RenderPossibleLink(v.StringValue())
		} else if v.Name == slashContext {
			if v.Type == discordgo.ApplicationCommandOptionString {
				extraContext = v.StringValue()
			} else if v.Type == discordgo.ApplicationCommandOptionInteger {
				extraContext = strconv.FormatInt(v.IntValue(), 10)
			}
		}
	}

	res := AdminOp(
		ctx,
		discord,
		rdb,
		db,
		i.Interaction.Member.User.ID,
		botId,
		op,
		types.AdminRedisContext{
			Reason:       &reason,
			ExtraContext: &extraContext,
		},
	)

	discord.InteractionRespond(i.Interaction, &discordgo.InteractionResponse{
		Type: discordgo.InteractionResponseChannelMessageWithSource,
		Data: &discordgo.InteractionResponseData{
			Content: res,
		},
	})
}
