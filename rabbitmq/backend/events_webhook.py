import aiohttp
from discord import Embed, Webhook

from modules.core import *
from rabbitmq.core import *


class Config:
    queue = "events_webhook_queue"
    name = "Events Webhook"
    description = "Send Webhooks for votes etc."

async def backend(state, json, *, webhook_url, webhook_type, api_token, id, webhook_target, event, context, event_type, event_time, event_id, webhook_secret, **kwargs):
    """
        RabbitMQ Backend to send webhooks

        webhook_url - The URL of the webhook
        webhook_type - The type of the webhook
        api_token - The API token of the bot/guild as a fallback
        id - The ID of the bot or user in question
        webhook_target - The target if the thing to send. Must be in enums.ObjTypes
        event - The event ID
        context - The context/main body of the event in question
        event_type - The type of event to send
        event_time - The time at which the event was made
        event_id - The event ID in question
        webhook_secret - The webhook secret
    """
    base_json = {"ctx": context, "m": {"e": event, "id": str(id), "eid": str(event_id), "wt": webhook_type, "t": event_type, "ts": event_time}} # The base JSON to base webhooks from 
    webhook_key = webhook_secret if webhook_secret else api_token

    if webhook_url in ("", None) or webhook_type is None or not (webhook_url.startswith("http://") or webhook_url.startswith("https://")):
        logger.debug(f"Not sending webhook to this bot as the URL or webhook type is clearly invalid: Webhook URL is {webhook_url} and Webhook Type is {webhook_type}")
        return False
    
    match (webhook_type, event):
    
        case (enums.WebhookType.discord, enums.APIEvents.bot_vote):
            if context.get("test"):
                user = await get_bot(int(context["user"])) # Get the test bot
            else:
                user = await get_user(int(context["user"])) # Get the user
            bot = await get_bot(int(id)) # Get the bot
            logger.debug(f"Got user {user} and bot {bot}")
            if not user or not bot:
                return False
            embed = Embed(
                title = "New Vote on Fates List",
                description=f"{user['username']}#{user['disc']} with ID {user['id']} has just cast a vote for {bot['username']} with ID {bot['id']} on Fates List!\nIt now has {context['votes']} votes!\n\nThank you for supporting this bot\n**GG**",
                color=242424
            )
            username = f"Fates List - {user['username']}#{user['disc']} ({user['id']})"
            async with aiohttp.ClientSession() as session:
                try:
                    webhook = Webhook.from_url(webhook_url, session = session)
                except discord.InvalidArgument:
                    return False

                await webhook.send(embed = embed, username = username)
            return True
    
        case (enums.WebhookType.vote, enums.APIEvents.bot_vote):
            json = base_json | {"id": str(context["user"]), "votes": context["votes"]}
        
        case (enums.WebhookType.fc, _):    
            json = base_json
        
        case _:
            return False
    
    logger.debug(inspect.cleandoc(f"""
        Going to send webhook:
            Method Given: {enums.WebhookType(webhook_type).name}
            JSON: {json}
            URL: {webhook_url}
            IDs: Mod -> {context.get('mod')}, User -> {context.get('user')}
            Bot ID: {id}"""))
            
    # Webhook sending with 7 retries
    resolved_error = False 
    for i in range(0, 7):
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post(webhook_url, json = json, headers = {"Authorization": webhook_key}, timeout = 15) as res:
                    if int(str(res.status)[0]) in (2, 4):
                        logger.success(
                            f"Webhook Post Returned {res.status}. Not retrying as this is either a success or a client side error"
                        )
                        return await _resolve_event(state, event_id, enums.WebhookResolver.posted)
                
                    else:
                        logger.warning(
                            f"URL did not return 2xx or a client-side 4xx error and sent {res.status} instead. Retrying...", 
                            "red"
                        )
        except Exception as exc:
            # Had an error sending
            logger.warning(f"Error when sending -> {type(exc).__name__}: {exc}")
            if not resolved_error:
                await _resolve_event(event_id, enums.WebhookResolver.error)
            resolved_error = True

async def _resolve_event(state, event_id, resolution):
    await state.postgres.execute("UPDATE bot_api_event SET posted = $1 WHERE id = $2", resolution, event_id)
