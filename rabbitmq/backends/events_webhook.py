import orjson
from aiohttp_requests import requests
import asyncio
from discord_webhook import DiscordWebhook, DiscordEmbed
from modules.core import get_bot, get_user, get_token, bot_add_event
from termcolor import colored, cprint
import modules.models.enums as enums


async def events_webhook_backend(webhook_url, webhook_type, api_token, id, webhook_target, event, context, event_id, webhook_secret):
    """
        RabbitMQ Backend to send webhooks

        webhook_url - The URL of the webhook
        webhook_type - The type of the webhook
        api_token - The API token of the bot/guild as a fallback
        id - The ID of the bot or user in question
        webhook_target - Either "bot" or "guild"
        event - The event name
        context - The context/main body of the event in question
        event_id - The event ID in question
        webhook_secret - The webhook secret
    """
    event_type = enums.APIEventTypes.bot if webhook_target == "bot" else enums.APIEventTypes.server
    webhook_key = webhook_secret if webhook_secret else api_token
    key = webhook_target + "_id"
    if webhook_url not in ["", None] and webhook_type is not None and (webhook_url.startswith("http://") or webhook_url.startswith("https://")):
        cont = True
        if webhook_type.upper() == "FC":
            f = requests.post
            json = {"event": event, "context": context, key: id, "event_id": str(event_id), "type": event_type}
            headers = {"Authorization": webhook_key}
        elif webhook_type.upper() == "DISCORD" and event == enums.APIEvents.bot_vote:
            webhook = DiscordWebhook(url=webhook_url)
            user = await get_user(int(context["user_id"])) # Get the user
            bot = await get_bot(id) # Get the bot
            embed = DiscordEmbed(
                title = "New Vote on Fates List",
                description=f"{user['username']} has just cast a vote for {bot['username']} on Fates List!\nIt now has {context['votes']} votes!\n\nThank you for supporting this bot\n**GG**",
                color=242424
            )
            webhook.add_embed(embed)
            response = webhook.execute()
            cont = False
        elif webhook_type.upper() == "VOTE" and event == enums.APIEvents.bot_vote:
            f = requests.post
            json = {"id": str(context["user"]), "votes": context["votes"]}
            headers = {"Authorization": webhook_key}
        else:
            cont = False
        if cont:
            if not json.get("context"):
                json["context"] = {}    
            json["context"]["mode"] = webhook_type.upper()
            cprint(f"Method Given: {webhook_type.upper()}", "blue")
            cprint(f"JSON: {json}\nFunction: {f}\nURL: {webhook_url}\nHeaders: {headers}\nID: {context.get('user_id')}, {context.get('mod')}, {context.get('user')}\nBot ID: {id}", "blue")
            
            # Webhook sending with 7 retries
            flagged = True # Are we 'flagged' for not yet sending webhook, default should be True 
            sent = 0 # Just a fall safe
            for i in range(1, 7):
                if not flagged or sent > 1: # If not flagged or sent more than one message
                    break
                res = await f(webhook_url, json = json, headers = headers)
                try:
                    if res.status != 200 and int(str(res.status))[0] != 4:
                        cprint("Invalid URL", "red")
                        continue
                except Exception as exc:
                    # Had an error sending
                    cprint(exc, "red")
                    sent+=1
                    flagged = False
                flagged = False
                sent+=1
