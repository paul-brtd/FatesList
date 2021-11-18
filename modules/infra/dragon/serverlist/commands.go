package serverlist

import (
	"dragon/common"
	"dragon/types"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/Fates-List/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/jackc/pgtype"
)

const good = 0x00ff00
const bad = 0xe74c3c

var (
	commands         = make(map[string]types.ServerListCommand)
	commandNameCache = make(map[string]string)
	numericRegex     *regexp.Regexp
)

func init() {
	var err error
	numericRegex, err = regexp.Compile("[^0-9]+")
	if err != nil {
		panic(err.Error())
	}
}

// Admin OP Getter
func cmdInit() {
	// Set sets a field
	commands["SET"] = types.ServerListCommand{
		InternalName: "set",
		Cooldown:     types.CooldownBucket{Name: "Update Bucket", InternalName: "update_bucket", Time: 5},
		Description:  "Sets a field, you may provide a pastebin link for long inputs",
		Perm:         2,
		Event:        types.EventNone,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "field",
				Description: "The field to update",
				Choices: []*discordgo.ApplicationCommandOptionChoice{
					{
						Name:  "Description",
						Value: "description",
					},
					{
						Name:  "Long Description",
						Value: "long_description",
					},
					{
						Name:  "Long Description Type",
						Value: "long_description_type",
					},
					{
						Name:  "Invite Code",
						Value: "invite_url",
					},
					{
						Name:  "Invite Channel ID",
						Value: "invite_channel",
					},
					{
						Name:  "Website",
						Value: "website",
					},
					{
						Name:  "CSS",
						Value: "css",
					},
					{
						Name:  "Banner (Server Card)",
						Value: "banner_card",
					},
					{
						Name:  "Banner (Server Page)",
						Value: "banner_page",
					},
					{
						Name:  "Keep Banner Decorations",
						Value: "keep_banner_decor",
					},
					{
						Name:  "State",
						Value: "state",
					},
					{
						Name:  "Recache/Update Server Now",
						Value: "recache",
					},
					{
						Name:  "Vanity",
						Value: "vanity",
					},
				},
				Required: true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "value",
				Description: "The value to set. Use 'none' to unset a field",
				Required:    true,
			},
		},
		Handler: func(context types.ServerListContext) string {
			fieldVal := getArg(context.Discord, context.Interaction, "field", false)
			field, ok := fieldVal.(string)
			if !ok {
				return "Field must be provided"
			}
			valueVal := getArg(context.Discord, context.Interaction, "value", true)
			value, ok := valueVal.(string)
			if !ok || value == "" || value == "none" {
				if field == "recache" || field == "invite_url" || field == "invite_channel" {
					value = ""
				} else {
					return "A value must be provided for this field"
				}
			}

			value = strings.Replace(value, "http://", "https://", -1)
			value = strings.Replace(value, "www.", "https://www.", -1)
			// Handle state
			if field == "state" {
				if value == "private_viewable" || value == "8" {
					value = "8"
				} else if value == "public" || value == "0" {

				} else {
					return "State must be one of (private_viewable, public)"
				}

				var currState pgtype.Int4
				err := context.Postgres.QueryRow(context.Context, "SELECT state FROM servers WHERE guild_id = $1", context.Interaction.GuildID).Scan(&currState)
				if err != nil {
					return err.Error()
				}
				if currState.Status != pgtype.Present {
					return "An error has occurred fetching your current status"
				}
				state := types.GetBotState(int(currState.Int))
				if state != types.BotStateApproved && state != types.BotStatePrivateViewable {
					return "You may not change the state of this server. Please contact Fates List Staff for more information"
				}
			}

			// Hand,e invite channel
			if field == "invite_channel" && value != "" {
				value = numericRegex.ReplaceAllString(value, "")
				_, err := context.Discord.State.Channel(value)
				if err != nil {
					return err.Error()
				}
			}

			// Handle keep banner decor
			if field == "keep_banner_decor" {
				if value == "true" || value == "yes" {
					value = "true"
				} else if value == "false" || value == "no" {
					value = "false"
				} else {
					return "Value for this field must be one of (yes, no)"
				}
			}

			// Handle website
			if field == "website" || field == "banner_card" || field == "banner_page" {
				if !strings.HasPrefix(value, "https://") {
					return "That is not a valid URL!"
				} else if strings.Contains(value, " ") {
					return "This field may not have spaces in the URL!"
				}
				if field == "banner_page" || field == "banner_card" {
					client := http.Client{Timeout: 5 * time.Second}
					var resp *http.Response
					var err error
					resp, err = client.Head(value)
					if err != nil || resp.StatusCode > 400 {
						resp, err = client.Get(value)
						if err != nil || resp.StatusCode > 400 {
							return "Could not resolve banner URL. Are you sure the URL works?"
						}
					}
					if !strings.HasPrefix(resp.Header.Get("Content-Type"), "image/") {
						return "This URL does not point to a valid image. Make sure the URL is valid and that there are no typos?"
					}
				}
			}

			// Handle invite url
			if field == "invite_url" && value != "" {
				if !strings.HasPrefix(value, "https://") {
					value = "https://discord.gg/" + value
				}
				client := http.Client{Timeout: 5 * time.Second}
				resp, err := client.Get(value)
				if err != nil {
					return "Could not resolve invite, possibly invalid?"
				}
				value = resp.Request.URL.String()
				codeLst := strings.Split(value, "/")
				value = codeLst[len(codeLst)-1]
				if value == "" {
					return "Invalid invite provided"
				}
				invites, err := context.Discord.GuildInvites(context.Interaction.GuildID)
				if err != nil {
					return "Something went wrong!\nError: " + err.Error()
				}

				invite := common.InviteFilter(invites, value)

				if invite == nil {
					return "This invite does not exist on this server. Are you sure the specified invite is for this server?\nFound code: " + value
				}
				if invite.MaxUses != 0 {
					return "This is a limited-use invite"
				} else if invite.Revoked {
					return "This invite has been revoked?"
				} else if invite.MaxAge != 0 || invite.Temporary {
					return "This invite is only temporary. For optimal user experience, all invites must be unlimited time and use"
				} else {
					value = "https://discord.gg/" + invite.Code // Not needed per say, but useful for readability
				}
			}

			var check pgtype.Int8

			context.Postgres.QueryRow(context.Context, "SELECT guild_id FROM servers WHERE guild_id = $1", context.Interaction.GuildID).Scan(&check)

			guild, err := context.Discord.State.Guild(context.Interaction.GuildID)
			if err != nil {
				return "Could not add guild because: " + err.Error()
			}

			var nsfw bool

			if guild.NSFWLevel == discordgo.GuildNSFWLevelExplicit || guild.NSFWLevel == discordgo.GuildNSFWLevelAgeRestricted {
				nsfw = true
			}

			if check.Status != pgtype.Present {
				apiToken := common.RandString(198)
				_, err = context.Postgres.Exec(context.Context, "INSERT INTO servers (guild_id, guild_count, api_token, name_cached, avatar_cached, nsfw) VALUES ($1, $2, $3, $4, $5, $6)", context.Interaction.GuildID, guild.MemberCount, apiToken, guild.Name, guild.IconURL(), nsfw)
				if err != nil {
					return "An error occurred while we were updating our database: " + err.Error()
				}
			} else {
				_, err = context.Postgres.Exec(context.Context, "UPDATE servers SET name_cached = $1, avatar_cached = $2, nsfw = $3, guild_count = $4 WHERE guild_id = $5", guild.Name, guild.IconURL(), nsfw, guild.MemberCount, guild.ID)
				if err != nil {
					return "An error occurred while we were updating our database: " + err.Error()
				}
			}
			if field != "recache" && field != "vanity" {
				context.Postgres.Exec(context.Context, "UPDATE servers SET "+field+" = $1 WHERE guild_id = $2", value, context.Interaction.GuildID)
			} else if field == "vanity" {
				value = strings.ToLower(strings.Replace(value, " ", "", -1))
				var check pgtype.Text
				context.Postgres.QueryRow(context.Context, "SELECT DISTINCT vanity_url FROM vanity WHERE lower(vanity_url) = $1 AND redirect != $2", value, guild.ID).Scan(&check)
				if check.Status == pgtype.Present {
					return "This vanity is currently in use"
				} else if strings.Contains(value, "/") {
					return "This vanity is not allowed"
				}
				_, err := context.Postgres.Exec(context.Context, "DELETE FROM vanity WHERE redirect = $1", guild.ID)
				if err != nil {
					return "An error occurred while we were updating our database: " + err.Error()
				}
				_, err = context.Postgres.Exec(context.Context, "INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 0, value, guild.ID)
				if err != nil {
					return "An error occurred while we were updating our database: " + err.Error()
				}
			}
			if field != "recache" {
				return "Successfully set " + field + "! Either see your servers page or use /get to verify that it got set to what you wanted!"
			}
			return "Recached server with " + strconv.Itoa(guild.MemberCount) + " members"
		},
	}
	commands["GET"] = types.ServerListCommand{
		InternalName: "get",
		Description:  "Gets a field",
		Cooldown:     types.CooldownBucket{Name: "Get Bucket", InternalName: "get_bucket", Time: 5},
		Perm:         2,
		Event:        types.EventNone,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "field",
				Description: "Which field to get",
				Choices: []*discordgo.ApplicationCommandOptionChoice{
					{
						Name:  "Description",
						Value: "description",
					},
					{
						Name:  "Long Description",
						Value: "long_description",
					},
					{
						Name:  "Long Description Type",
						Value: "long_description_type",
					},
					{
						Name:  "State",
						Value: "state",
					},
					{
						Name:  "NSFW Status",
						Value: "nsfw",
					},
					{
						Name:  "Website",
						Value: "website",
					},
					{
						Name:  "Invite Code",
						Value: "invite_url",
					},
					{
						Name:  "Invite Channel ID",
						Value: "invite_channel",
					},
					{
						Name:  "Banner (Server Card)",
						Value: "banner_card",
					},
					{
						Name:  "Banner (Server Page)",
						Value: "banner_page",
					},
					{
						Name:  "CSS",
						Value: "css",
					},
					{
						Name:  "Server API Token",
						Value: "api_token",
					},
					{
						Name:  "Vanity",
						Value: "vanity",
					},
				},
				Required: true,
			},
		},
		Handler: func(context types.ServerListContext) string {
			fieldVal := getArg(context.Discord, context.Interaction, "field", false)
			field, ok := fieldVal.(string)
			if !ok {
				return "Field must be provided"
			}
			if field == "api_token" && !checkPerms(context.Discord, context.Interaction, 3) {
				return ""
			}

			var v pgtype.Text

			if field == "vanity" {
				context.Postgres.QueryRow(context.Context, "SELECT vanity_url FROM vanity WHERE type = $1 AND redirect = $2", 0, context.Interaction.GuildID).Scan(&v)
			} else {
				context.Postgres.QueryRow(context.Context, "SELECT "+field+"::text FROM servers WHERE guild_id = $1", context.Interaction.GuildID).Scan(&v)
			}

			if v.Status != pgtype.Present {
				return field + " is not set!"
			}

			if len(v.String) > 1994 {
				sendIResponseEphemeral(context.Discord, context.Interaction, "Value of `"+field+"`", false, v.String)
			} else {
				sendIResponseEphemeral(context.Discord, context.Interaction, "```"+v.String+"```", false)
			}
			return ""
		},
	}

	commands["HELP"] = types.ServerListCommand{
		InternalName: "help",
		Description:  "More information on how to use Fates List Server Listing",
		SlashOptions: []*discordgo.ApplicationCommandOption{},
		Handler: func(context types.ServerListContext) string {
			intro := "**Welcome to Fates List**\n" +
				"If you're reading this, you probably already know what server listing (and slash commands) are. This guide will not go over that"

			syntax := "**Slash command syntax**\n" +
				"This guide will use the following syntax for slash commands: `/command option:foo anotheroption:bar`"

			faqBasics := "**How do I add my server?**+\n" +
				"Good question. Just do `/set field:descriotion value:My lovely description`. You **can/should** set a long description using " +
				"`/set field:long_description value:My really really long description`. **For really long descriptions, you can also create " +
				"a paste on pastebin and provide the pastebin link as the value**"

			faqState := "**What is the 'State' option?**\n" +
				"Long story short, state allows you to configure the privacy of your server and in the future may do other things as well. " +
				"*What is this privacy, you ask?* Well, if you are being raided and you wish to stop people from joining your server during a " +
				"raid, then you can simply set the state of your server to `private_viewable` or `8`. This will stop it from being indexed " +
				"and will *also* block users from joining your server until you're ready to set the state to `public` or `0`."

			helpPage1 := strings.Join([]string{intro, syntax, faqBasics, faqState}, "\n\n")
			sendIResponseEphemeral(context.Discord, context.Interaction, helpPage1, false)
			return ""
		},
	}

	// Load command name cache to map internal name to the command
	for cmdName, v := range commands {
		commandNameCache[v.InternalName] = cmdName
	}
}

func GetCommandSpew() string {
	return spew.Sdump("Admin commands loaded: ", commands)
}
