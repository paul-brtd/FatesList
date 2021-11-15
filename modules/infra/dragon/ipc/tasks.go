package ipc

import (
	"context"
	"dragon/common"
	"dragon/types"
	"encoding/json"
	"strconv"
	"strings"

	"github.com/bwmarrin/discordgo"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

func taskHandle(ctx context.Context, discord *discordgo.Session, rdb *redis.Client, db *pgxpool.Pool, task_id string) {
	delCmd := func() {
		rdb.LRem(ctx, "bt_ongoing", 0, task_id)
		rdb.Del(ctx, task_id)
	}

	pgctx := context.Background()

	log.Info("Going to handle task id: ", task_id)
	cmd_str := rdb.Get(ctx, task_id).Val()
	if cmd_str == "" {
		log.Warning("No command data found!")
		delCmd()
		return
	}

	var task types.FatesTask
	err := json.Unmarshal([]byte(cmd_str), &task)
	if err != nil {
		log.Error(err)
		return
	}

	switch task.Op {
	case types.OPWebhook:
		var webhook types.WebhookData
		log.Debug("Task Data: ", task.Data)
		err := json.Unmarshal([]byte(task.Data), &webhook)
		if err != nil {
			log.Error(err)
			return
		}

		var table_name string

		if webhook.Bot {
			table_name = "bots"
		} else {
			table_name = "servers"
		}

		ok, webhookType, secret, webhookURL := common.GetWebhook(pgctx, table_name, webhook.Id, db)

		if !ok {
			log.Warning("Error in getting webhook")
			delCmd()
			return
		}

		// Add event
		eventId := common.CreateUUID()
		log.Debug("Created event id of: ", eventId)
		_, err = db.Exec(pgctx, "INSERT INTO bot_api_event (bot_id, event, type, context, id) VALUES ($1, $2, $3, $4, $5)", webhook.Id, webhook.Event, webhook.EventType, task.Context, eventId)

		if err != nil {
			log.Error(err)
			return
		}

		metadata := types.EventMetadata{
			Event:     webhook.Event,
			User:      webhook.User,
			Timestamp: webhook.Timestamp,
			EventId:   eventId,
			EventType: webhook.EventType,
		}

		if webhook.Event == types.EventBotVote && webhookType == types.VoteWebhook {
			vote := types.FatesVote{
				User:      webhook.User,
				VoteCount: webhook.VoteCount,
				Context:   task.Context,
				Metadata:  metadata,
			}
			vote_b, err := json.Marshal(vote)
			if err != nil {
				log.Error(err)
				return
			}
			vote_str := string(vote_b)
			log.Debug("Sending vote json of: ", vote_str)
			common.WebhookReq(ctx, db, eventId, webhookURL, secret, vote_str, 0)
		} else if webhook.Event == types.EventBotVote && webhookType == types.DiscordWebhook {
			if !strings.HasPrefix(webhookURL, "https://discord.com/api/webhooks") {
				log.WithFields(log.Fields{
					"url": webhookURL,
				}).Warning("Invalid webhook URL")
			}
			parts := strings.Split(webhookURL, "/")
			if len(parts) < 7 {
				log.WithFields(log.Fields{
					"url": webhookURL,
				}).Warning("Invalid webhook URL")
				delCmd()
				return
			}
			webhookId := parts[5]
			webhookToken := parts[6]
			userObj, err := discord.User(webhook.User)
			if err != nil {
				log.WithFields(log.Fields{
					"user": webhook.User,
				}).Warning(err)
			}

			botObj, err := discord.User(webhook.Id)
			if err != nil {
				log.WithFields(log.Fields{
					"user": webhook.User,
				}).Warning(err)
			}

			userWithDisc := userObj.Username + "#" + userObj.Discriminator

			_, err = discord.WebhookExecute(webhookId, webhookToken, true, &discordgo.WebhookParams{
				Username: "Fates List - " + userWithDisc + " (" + userObj.ID + ")",
				Embeds: []*discordgo.MessageEmbed{
					{
						Title:       "New Vote on Fates List",
						Description: userWithDisc + " with ID " + userObj.ID + " has just cast a vote for " + botObj.Username + " with ID " + botObj.ID + " on Fates List!\nIt now has " + strconv.Itoa(webhook.VoteCount) + " votes!\n\nThank you for supporting this bot\n**GG**",
						Color:       242424,
					},
				},
			})

			if err != nil {
				log.Error(err)
				return
			}

			_, err = db.Exec(ctx, "UPDATE bot_api_event SET posted = $1 WHERE id = $2", types.WebhookPostSuccess, eventId)
			if err != nil {
				log.Error(err)
				return
			}

		} else if webhookType == types.FatesWebhook {
			data := types.Event{
				Context:  task.Context,
				Metadata: metadata,
			}
			data_json, err := json.Marshal(data)
			if err != nil {
				log.Error(err)
				return
			}
			data_str := string(data_json)
			log.Debug("Sending json of: ", data_str)
			common.WebhookReq(ctx, db, eventId, webhookURL, secret, data_str, 0)
		}
	}
	delCmd()
}
