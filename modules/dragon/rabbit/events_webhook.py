import aiohttp
from discord import Embed, Webhook

from modules.core import *
from lynxfall.rabbit.core import *


class Config:
    queue = "events_webhook_queue"
    name = "Events Webhook"
    description = "Send Webhooks for votes etc."

async def backend(
    state, 
    json, 
    *, 
    id, 
    target,
    event, 
    ctx, 
    t, 
    ts, 
    eid, 
    **kwargs
):
    """
        RabbitMQ Backend to send webhooks

        id - The ID of the bot or user in question
        target - The target for the thing to send (bot/guild).
        event - The event name
        ctx - The context/main body of the event in question
        t - The type of event to send
        ts - The time at which the event was made
        eid - The event ID in question
    """
    if target not in ("bot",):
        return

    data = await state.postgres.fetchrow(
        f"SELECT webhook_type, webhook, api_token, webhook_secret FROM {target}s WHERE bot_id = $1", id
    )
    base_json = {"ctx": ctx, "m": {"e": event, "id": str(id), "eid": str(eid), "wt": data["webhook_type"], "t": t, "ts": ts}} # The base JSON to base webhooks from 
    webhook_key = data["webhook_secret"] if data["webhook_secret"] else data["api_token"]

    if not data["webhook"] or data["webhook_type"] is None or not data["webhook"].startswith(("http://", "https://")):
        logger.debug(f"Not sending webhook to this bot as the URL or webhook type is clearly invalid: Webhook URL is {data['webhook']} and Webhook Type is {data['webhook_type']}")
        return False
    
    match (data["webhook_type"], event):
    
        case (enums.WebhookType.discord, enums.APIEvents.bot_vote):
            if ctx.get("test"):
                user = await get_bot(int(ctx["user"])) # Get the test bot
            else:
                user = await get_user(int(ctx["user"])) # Get the user
            bot = await get_bot(int(id)) # Get the bot
            logger.debug(f"Got user {user} and bot {bot}")
            if not user or not bot:
                return False
            embed = Embed(
                title = "New Vote on Fates List",
                description=f"{user['username']}#{user['disc']} with ID {user['id']} has just cast a vote for {bot['username']} with ID {bot['id']} on Fates List!\nIt now has {ctx['votes']} votes!\n\nThank you for supporting this bot\n**GG**",
                color=242424
            )
            username = f"Fates List - {user['username']}#{user['disc']} ({user['id']})"
            async with aiohttp.ClientSession() as session:
                try:
                    webhook = Webhook.from_url(data["webhook"], session = session)
                except discord.InvalidArgument:
                    return False

                await webhook.send(embed = embed, username = username)
            return True
    
        case (enums.WebhookType.vote, enums.APIEvents.bot_vote):
            json = base_json | {"id": str(ctx["user"]), "votes": ctx["votes"]}
        
        case (enums.WebhookType.fc, _):    
            json = base_json
        
        case _:
            return False
    
    logger.debug(inspect.cleandoc(f"""
        Going to send webhook:
            Method Given: {enums.WebhookType(data['webhook_type']).name}
            JSON: {json}
            URL: {data['webhook']}
            IDs: Mod -> {ctx.get('mod')}, User -> {ctx.get('user')}
            Bot ID: {id}"""))
            
    # Webhook sending with 7 retries
    resolved_error = False 
    for i in range(0, 7):
        try:
            async with aiohttp.ClientSession() as sess:
                async with sess.post(data["webhook"], json = json, headers = {"Authorization": webhook_key}, timeout = 15) as res:
                    if int(str(res.status)[0]) in (2, 4):
                        logger.success(
                            f"Webhook Post Returned {res.status}. Not retrying as this is either a success or a client side error"
                        )
                        return await _resolve_event(state, eid, enums.WebhookResolver.posted)
                
                    else:
                        logger.warning(
                            f"URL did not return 2xx or a client-side 4xx error and sent {res.status} instead. Retrying...", 
                            "red"
                        )
        except Exception as exc:
            # Had an error sending
            logger.warning(f"Error when sending -> {type(exc).__name__}: {exc}")
            if not resolved_error:
                await _resolve_event(state, eid, enums.WebhookResolver.error)
            resolved_error = True

async def _resolve_event(state, eid, resolution):
    await state.postgres.execute("UPDATE bot_api_event SET posted = $1 WHERE id = $2", resolution, eid)
