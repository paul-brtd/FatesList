package serverlist

import (
	"context"
	"dragon/common"
	"dragon/types"
	"encoding/json"
	"fmt"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/Fates-List/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

const good = 0x00ff00
const bad = 0xe74c3c

var (
	commands         = make(map[string]types.ServerListCommand)
	commandNameCache = make(map[string]string)
	numericRegex     *regexp.Regexp
)

func dbError(err error) string {
	return "An error occurred while we were updating our database: " + err.Error()
}

func AddRecacheGuild(context context.Context, postgres *pgxpool.Pool, guild *discordgo.Guild) string {
	// Adds or recaches a guild
	if guild == nil {
		return "Guild cannot be nil"
	}

	var check pgtype.Int8
	postgres.QueryRow(context, "SELECT guild_id FROM servers WHERE guild_id = $1", guild.ID).Scan(&check)

	var nsfw bool
	if guild.NSFWLevel == discordgo.GuildNSFWLevelExplicit || guild.NSFWLevel == discordgo.GuildNSFWLevelAgeRestricted {
		nsfw = true
	}

	var memberCount int
	if guild.MemberCount > guild.ApproximateMemberCount {
		memberCount = guild.MemberCount
	} else {
		memberCount = guild.ApproximateMemberCount
	}

	var err error
	if check.Status != pgtype.Present {
		apiToken := common.RandString(198)
		_, err = postgres.Exec(context, "INSERT INTO servers (guild_id, guild_count, api_token, name_cached, avatar_cached, nsfw) VALUES ($1, $2, $3, $4, $5, $6)", guild.ID, memberCount, apiToken, guild.Name, guild.IconURL(), nsfw)
		if err != nil {
			return dbError(err)
		}
	} else {
		_, err = postgres.Exec(context, "UPDATE servers SET name_cached = $1, avatar_cached = $2, nsfw = $3, guild_count = $4 WHERE guild_id = $5", guild.Name, guild.IconURL(), nsfw, guild.MemberCount, guild.ID)
		if err != nil {
			return dbError(err)
		}
	}
	return ""
}

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
					{
						Name:  "Webhook Secret",
						Value: "webhook_secret",
					},
					{
						Name:  "Webhook URL",
						Value: "webhook",
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

			// Handle webhook secret and url
			if (field == "webhook_secret" || field == "webhook") && !checkPerms(context.Discord, context.Interaction, 3) {
				return ""
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
			if field == "website" || field == "banner_card" || field == "banner_page" || field == "webhook" {
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

			guild, err := context.Discord.State.Guild(context.Interaction.GuildID)
			if err != nil {
				return "Could not find guild because: " + err.Error()
			}

			dbErr := AddRecacheGuild(context.Context, context.Postgres, guild)
			if dbErr != "" {
				return dbErr
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

			// Update server audit log here
			var auditVal string
			if len(value) > 10 {
				auditVal = value[:10] + "..."
			} else {
				auditVal = value
			}

			auditLogAction := map[string]interface{}{
				"user_id":    context.Interaction.Member.User.ID,
				"username":   context.Interaction.Member.User.Username,
				"user_perms": context.Interaction.Member.Permissions,
				"action_id":  common.CreateUUID(),
				"field":      field,
				"value":      auditVal,
				"ts":         float64(time.Now().Unix()) + 0.001, // Make sure its a float by adding 0.001
			}

			auditLogActionBytes, err := json.Marshal(auditLogAction)

			if err != nil {
				return dbError(err)
			}

			_, err = context.Postgres.Exec(context.Context, "UPDATE servers SET audit_logs = audit_logs || $1 WHERE guild_id = $2", []string{string(auditLogActionBytes)}, guild.ID)

			if err != nil {
				return dbError(err)
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
						Name:  "Webhook Secret",
						Value: "webhook_secret",
					},
					{
						Name:  "Vanity",
						Value: "vanity",
					},
					{
						Name:  "User Whitelist",
						Value: "user_whitelist",
					},
					{
						Name:  "User Blacklist",
						Value: "user_blacklist",
					},
					{
						Name:  "Audit Logs",
						Value: "audit_logs",
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
			if (field == "api_token" || field == "webhook_secret") && !checkPerms(context.Discord, context.Interaction, 3) {
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

			if field == "audit_logs" {
				var auditLogData []map[string]interface{}
				if len(v.String) > 3 {
					// Fix output for encoding/json
					v.String = strings.Replace(strings.Replace(strings.Replace("["+v.String[2:len(v.String)-2]+"]", "\\", "", -1), "\"{", "{", -1), "}\"", "}", -1)
					err := json.Unmarshal([]byte(v.String), &auditLogData)
					if err != nil {
						return err.Error()
					}
					auditLogPretty, err := json.MarshalIndent(auditLogData, "", "    ")
					if err != nil {
						return err.Error()
					}
					v.String = string(auditLogPretty)
				}
			}

			if len(v.String) > 1994 {
				sendIResponseEphemeral(context.Discord, context.Interaction, "Value of `"+field+"`", false, v.String)
			} else {
				sendIResponseEphemeral(context.Discord, context.Interaction, "```"+v.String+"```", false)
			}
			return ""
		},
	}

	commands["VOTE"] = types.ServerListCommand{
		InternalName: "vote",
		Description:  "Vote for this server!",
		Perm:         1,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionBoolean,
				Name:        "test",
				Description: "Whether or not to create a 'test' vote. This vote is not counted. This is Manage Server/Admin only",
			},
		},
		Handler: func(context types.ServerListContext) string {
			testVal := getArg(context.Discord, context.Interaction, "test", false)
			test, ok := testVal.(bool)
			if !ok {
				test = false
			}

			if test && !checkPerms(context.Discord, context.Interaction, 3) {
				return ""
			}

			key := "vote_lock+server:" + context.Interaction.Member.User.ID
			check := context.Redis.PTTL(context.Context, key).Val()
			debug := "**DEBUG (for nerds)**\nRedis TTL: " + strconv.FormatInt(check.Milliseconds(), 10) + "\nKey: " + key + "\nTest: " + strconv.FormatBool(test)
			var voteMsg string // The message that will be shown to the use on a successful vote

			if check.Milliseconds() == 0 || test {
				var userId string
				if test {
					userId = "519850436899897346"
				} else {
					userId = context.Interaction.Member.User.ID
				}

				var votesDb pgtype.Int8

				err := context.Postgres.QueryRow(context.Context, "SELECT votes FROM servers WHERE guild_id = $1", context.Interaction.GuildID).Scan(&votesDb)

				if err != nil {
					return dbError(err)
				}

				votes := votesDb.Int + 1

				eventId := common.CreateUUID()

				voteEvent := map[string]interface{}{
					"votes": votes,
					"id":    userId,
					"ctx": map[string]interface{}{
						"user":  userId,
						"votes": votes,
						"test":  test,
					},
					"m": map[string]interface{}{
						"event": types.EventServerVote,
						"user":  userId,
						"t":     -1,
						"ts":    float64(time.Now().Unix()) + 0.001, // Make sure its a float by adding 0.001
						"eid":   eventId,
					},
				}

				vote_b, err := json.Marshal(voteEvent)
				if err != nil {
					return dbError(err)
				}
				voteStr := string(vote_b)

				ok, webhookType, secret, webhookURL := common.GetWebhook(context.Context, "servers", context.Interaction.GuildID, context.Postgres)
				if !ok {
					voteMsg = "You have successfully voted for this server (note: this server does not support vote rewards)"
				} else {
					voteMsg = "You have successfully voted for this server"
					go common.WebhookReq(context.Context, context.Postgres, eventId, webhookURL, secret, voteStr, 0)
					log.Debug("Got webhook type of " + strconv.Itoa(int(webhookType)))
				}

				if !test {
					context.Postgres.Exec(context.Context, "UPDATE servers SET votes = votes + 1 WHERE guild_id = $1", context.Interaction.GuildID)
					context.Redis.Set(context.Context, key, 0, 8*time.Hour)
				}
			} else {
				hours := check / time.Hour
				mins := (check - (hours * time.Hour)) / time.Minute
				secs := (check - (hours*time.Hour + mins*time.Minute)) / time.Second
				voteMsg = fmt.Sprintf("Please wait %02d hours, %02d minutes %02d seconds", hours, mins, secs)
			}

			return voteMsg + "\n\n" + debug
		},
	}

	commands["BUMP"] = types.ServerListCommand{
		InternalName: "bump",
		AliasTo:      "VOTE",
	}

	commands["HELP"] = types.ServerListCommand{
		InternalName: "help",
		Perm:         1,
		Description:  "More information on how to use Fates List Server Listing",
		SlashOptions: []*discordgo.ApplicationCommandOption{},
		Handler: func(context types.ServerListContext) string {
			intro := "**Welcome to Fates List**\n" +
				"If you're reading this, you probably already know what server listing (and slash commands) are. This guide will not go over that"

			syntax := "**Slash command syntax**\n" +
				"This guide will use the following syntax for slash commands: `/command option:foo anotheroption:bar`"

			faqBasics := "**How do I add my server?**+\n" +
				"Good question. Your server should usually be automatically added for you once you add the bot to your server. " +
				"Just set a description using `/set field:descriotion value:My lovely description`. If you do not do so, the description " +
				"will be randomly set for you and it will likely not be what you want. You **should** set a long description using " +
				"`/set field:long_description value:My really really long description`. **For really long descriptions, you can also create " +
				"a paste on pastebin and provide the pastebin link as the value**"

			faqState := "**What is the 'State' option?**\n" +
				"Long story short, state allows you to configure the privacy of your server and in the future may do other things as well. " +
				"*What is this privacy, you ask?* Well, if you are being raided and you wish to stop people from joining your server during a " +
				"raid, then you can simply set the state of your server to `private_viewable` or `8`. This will stop it from being indexed " +
				"and will *also* block users from joining your server until you're ready to set the state to `public` or `0`."

			faqVoteRewards := "**Vote Rewards**\n" +
				"You can reward users for voting for your server using vote rewards. This can be things like custom roles or extra perks! " +
				"In order to use vote rewards, you will either need to get your API Token (or your Webhook Secret if you have one set and " +
				"wish to use webhooks) or you will need to use our websocket API to listen for events. Once you have gotten a server vote " +
				"event, you can then give rewards for voting. The event number for server votes is `71`"

			faqAllowlist := "**Server Allow List**\n" +
				"For invite-only/private servers, you can/should use a **user whitelist** to prevent users outside the user whitelist from " +
				"joining your server. If you do not have any users on your user whitelist, anyone may join your server. User blacklists allow " +
				"you to blacklist bad users from getting an invite to your server via Fates List"

			helpPages := []string{
				strings.Join([]string{intro, syntax, faqBasics, faqState, faqVoteRewards}, "\n\n"),
				strings.Join([]string{faqAllowlist}, "\n\n"),
			}

			for i, v := range helpPages {
				if i == 0 {
					sendIResponse(context.Discord, context.Interaction, "defer", false)
				}
				sendIResponseEphemeral(context.Discord, context.Interaction, v, false)
			}

			context.Discord.InteractionResponseDelete(context.Discord.State.User.ID, context.Interaction)

			return ""
		},
	}
	commands["ALLOWLIST"] = types.ServerListCommand{
		InternalName: "allowlist",
		Description:  "Modifies the servers allowlist",
		Perm:         3,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "type",
				Description: "The list to modify",
				Choices: []*discordgo.ApplicationCommandOptionChoice{
					{
						Name:  "Whitelist",
						Value: "user_whitelist",
					},
					{
						Name:  "Blacklist",
						Value: "user_blacklist",
					},
				},
				Required: true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "action",
				Description: "What to do on the allowlist",
				Choices: []*discordgo.ApplicationCommandOptionChoice{
					{
						Name:  "Add User",
						Value: "add_user",
					},
					{
						Name:  "Remove User",
						Value: "delete_user",
					},
					{
						Name:  "Clear",
						Value: "clear",
					},
				},
				Required: true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionUser,
				Name:        "user",
				Description: "The user to add/remove. Can be a mention as well",
			},
		},
		Handler: func(context types.ServerListContext) string {
			return "Work in progress, coming soon :)"
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
