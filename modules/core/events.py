"""
Handle API Events, webhooks and websockets
"""

from .imports import *
from .cache import get_user, get_bot

async def bot_add_ws_event(bot_id: int, ws_event: dict) -> None:
    """A WS Event must have the following format:
        - {id: Event ID, event: Event Name, context: Context, type: Event Type}
    """
    curr_ws_events = await redis_db.hget(str(bot_id), key = "ws") # Get all the websocket events from the ws key
    if curr_ws_events is None:
        curr_ws_events = {} # No ws events means empty dict
    else:
        curr_ws_events = orjson.loads(curr_ws_events) # Otherwise, orjson load the current events
    id = ws_event["id"] # Get id
    del ws_event["id"] # Remove id
    curr_ws_events[id] = ws_event # Add event to current ws events
    await redis_db.hset(str(bot_id), key = "ws", value = orjson.dumps(curr_ws_events)) # Add it to redis
    await redis_db.publish(str(bot_id), orjson.dumps({id: ws_event})) # Publish it to consumers

async def bot_get_events(bot_id: int, filter: list = None, exclude: list = None):
    # As a replacement/addition to webhooks, we have API events as well to allow you to quickly get old and new events with their epoch

    extra = ""
    extra_params = []
    i = 2 # Keep track of parameters
    if filter:
        extra = f"AND event = ANY(${i}::text[]) "
        extra_params.append(filter)
        i+=1
    elif exclude:
        extra += f"AND event != ANY(${i}::text[])"
        extra_params.append(exclude)
        i+=1
    api_data = await db.fetch(f"SELECT bot_id, epoch, event, context, id FROM bot_api_event WHERE bot_id = $1 {extra} ORDER BY epoch", bot_id, *extra_params)
    api_data = [{"bot_id": str(obj["bot_id"]), "epoch": str(obj["epoch"]), "event": obj["event"], "context": orjson.loads(obj["context"]), "id": obj["id"]} for obj in api_data]
    return {"events": api_data}

async def bot_add_event(bot_id: int, event: str, context: dict, *, send_event = True):
    if type(context) == dict:
        pass
    else:
        raise TypeError("Event must be a dict")

    id = uuid.uuid4()
    api_token = await db.fetchval("SELECT api_token FROM bots WHERE bot_id = $1", bot_id)
    if api_token is None:
        return
    asyncio.create_task(db.execute("INSERT INTO bot_api_event (bot_id, epoch, event, context, id) VALUES ($1, $2, $3, $4, $5)", bot_id, time.time(), event, orjson.dumps(context).decode("utf-8"), id))
    webh = await db.fetchrow("SELECT webhook, webhook_type FROM bots WHERE bot_id = $1", int(bot_id))
    if webh and send_event:
        asyncio.create_task(_event_webhook_sender(webh["webhook"], webh["webhook_type"], api_token, bot_id, "bot", event, context, id))
    asyncio.create_task(bot_add_ws_event(bot_id, {"payload": "event", "id": str(id), "event": event, "context": context}))
    return id

async def _event_webhook_sender(webhook_url, webhook_type, api_token, id, webhook_target, event, context, event_id):
    """
        Internal function to send webhooks

        webhook_url - The URL of the webhook
        webhook_type - The type of the webhook
        api_token - The API token of the webhook
        id - The ID of the bot or user in question
        webhook_target - Either "bot" or "guild"
        event - The event name
        context - The context/main body of the event in question
        event_id - The event ID in question
    """
    key = webhook_target + "_id"
    if webhook_url not in ["", None] and webhook_type is not None:
        cont = True
        if webhook_type.upper() == "FC":
            f = requests.post
            json = {"event": event, "context": context, key: id, "event_id": str(event_id), "type": webhook_target}
            headers = {"Authorization": api_token}
        elif webhook_type.upper() == "DISCORD" and event in "vote" and webhook_target == "bot":
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
        elif webhook_type.upper() == "VOTE" and event == "vote":
            f = requests.post
            json = {"id": str(context["user_id"]), "votes": context["votes"]}
            headers = {"Authorization": api_token}
        else:
            cont = False
        if cont:
            print(f"Method Given: {webhook_type.upper()}")
            print(f"JSON: {json}\nFunction: {f}\nURL: {webhook_url}\nHeaders: {headers}")
            json = json | {"payload": "event", "mode": webhook_type.upper()}
            await f(webhook_url, json = json, headers = headers)
