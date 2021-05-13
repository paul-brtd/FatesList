import orjson
from aiohttp_requests import requests
import asyncio
from discord_webhook import DiscordWebhook, DiscordEmbed
from modules.core import get_bot, get_user, get_token, bot_add_event
from termcolor import colored, cprint
import modules.models.enums as enums

async def events_webhook_backend(webhook_url, webhook_type, api_token, id, webhook_target, event, context, event_type, event_time, event_id, webhook_secret):
    """
        RabbitMQ Backend to send webhooks

        webhook_url - The URL of the webhook
        webhook_type - The type of the webhook
        api_token - The API token of the bot/guild as a fallback
        id - The ID of the bot or user in question
        webhook_target - The target if the thing to send. Must be in enums.ObjTypes
        event - The event name
        context - The context/main body of the event in question
        event_type - The type of event to send
        event_time - The time at which the event was made
        event_id - The event ID in question
        webhook_secret - The webhook secret
    """
    webhook_key = webhook_secret if webhook_secret else api_token
    if webhook_url not in ["", None] and webhook_type is not None and (webhook_url.startswith("http://") or webhook_url.startswith("https://")):
        cont = True
        if webhook_type == enums.WebhookType.fc:
            f = requests.post
            json = {"e": event, "ctx": context | {"m": {"t": webhook_target, "id": id, "eid": str(event_id), "wt": webhook_type}}, "t": event_type, "ts": event_time}
            headers = {"Authorization": webhook_key}
        elif webhook_type == enums.WebhookType.discord and event == enums.APIEvents.bot_vote:
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
        elif webhook_type == enums.WebhookType.vote and event == enums.APIEvents.bot_vote:
            f = requests.post
            json = {"id": str(context["user"]), "votes": context["votes"], "m": {"t": webhook_target, "wt": webhook_type, "eid": str(event_id)}, "ts": event_time, "e": "vote_bot", "t": "webhook", "ctx": context}
            headers = {"Authorization": webhook_key}
        else:
            cont = False
        if cont:
            cprint(f"Method Given: {enums.WebhookType(webhook_type).name}", "blue")
            cprint(f"JSON: {json}\nFunction: {f}\nURL: {webhook_url}\nHeaders: {headers}\nID: {context.get('user_id')}, {context.get('mod')}, {context.get('user')}\nBot ID: {id}", "blue")
            
            # Webhook sending with 7 retries
            flagged = True # Are we 'flagged' for not yet sending webhook, default should be True 
            sent = 0 # Just a fall safe
            for i in range(1, 7):
                if not flagged or sent > 1: # If not flagged or sent more than one message
                    break
                res = await f(webhook_url, json = json, headers = headers)
                try:
                    if res.status != 200 and int(str(res.status)[0]) != 4:
                        cprint("Invalid URL", "yellow")
                        continue
                    elif res.status != 200:
                        raise ValueError("URL did not return 200. Retrying...")
                except Exception as exc:
                    # Had an error sending
                    cprint(exc, "yellow")
                    sent+=1
                    flagged = False
                flagged = False
                sent+=1
            await db.execute("UPDATE bot_api_event SET posted = true WHERE id = $1", event_id)
