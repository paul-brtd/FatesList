"""
Handle API Events, webhooks and websockets
"""

from .imports import *
from .cache import get_user, get_bot
from .rabbitmq import *

async def bot_add_ws_event(bot_id: int, ws_event: dict, *, id: Optional[uuid.UUID] = None) -> None:
    """A WS Event must have the following format:
        - {e: Event Name, t: Event Type (Optional), ctx: Context, m: Event Metadata}
    """
    if not id:
        id = uuid.uuid4()
    id = str(id)
    if "m" not in ws_event.keys():
        ws_event["m"] = {}
    ws_event["m"]["eid"] = id
    ws_event["m"]["ts"] = time.time()
    curr_ws_events = await redis_db.hget(str(bot_id), key = "ws") # Get all the websocket events from the ws key
    if curr_ws_events is None:
        curr_ws_events = {} # No ws events means empty dict
    else:
        curr_ws_events = orjson.loads(curr_ws_events) # Otherwise, orjson load the current events
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
    api_data = await db.fetch(f"SELECT epoch, event AS e, context AS ctx, id, type FROM bot_api_event WHERE bot_id = $1 {extra} ORDER BY epoch", bot_id, *extra_params)
    api_data = [{"ctx": orjson.loads(obj["ctx"]), "m": {"e": obj["e"], "eid": obj["id"], "ts": str(obj["epoch"]), "t": obj["type"]}} for obj in api_data]
    return {"events": api_data}

async def bot_add_event(bot_id: int, event: int, context: dict, t: Optional[int] = None, *, send_event = True):
    if type(context) == dict:
        pass
    else:
        raise TypeError("Event must be a dict")

    id = uuid.uuid4()
    api_token = await db.fetchval("SELECT api_token FROM bots WHERE bot_id = $1", bot_id)
    if api_token is None:
        return
    event_time = time.time()
    asyncio.create_task(db.execute("INSERT INTO bot_api_event (bot_id, epoch, event, type, context, id) VALUES ($1, $2, $3, $4, $5, $6)", bot_id, event_time, event, t, orjson.dumps(context).decode("utf-8"), id))
    webh = await db.fetchrow("SELECT webhook, webhook_type, webhook_secret FROM bots WHERE bot_id = $1", int(bot_id))
    if webh and send_event:
        await add_rmq_task("events_webhook_queue", {
            "webhook_url": webh["webhook"], 
            "webhook_type": webh["webhook_type"],
            "webhook_secret": webh["webhook_secret"],
            "api_token": api_token, 
            "id": bot_id, 
            "webhook_target": enums.ObjTypes.bot, 
            "event": event, 
            "context": context,
            "event_type": t,
            "event_time": event_time,
            "event_id": id
        })
        asyncio.create_task(bot_add_ws_event(bot_id, {"ctx": context, "m": {"t": t, "ts": event_time, "e": event}}, id = id))
    return id
