"""
Handle API Events, webhooks and websockets
"""

from .imports import *

async def add_ws_event(bot_id: int, ws_event: dict) -> None:
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

async def get_events(api_token: Optional[str] = None, bot_id: Optional[str] = None, event_id: Optional[uuid.UUID] = None):
    if api_token is None and bot_id is None:
        return {"events": []}
    if api_token is None:
        bid = await db.fetchrow("SELECT bot_id, servers FROM bots WHERE bot_id = $1", bot_id)
    else:
        bid = await db.fetchrow("SELECT bot_id, servers FROM bots WHERE api_token = $1", api_token)
    if bid is None:
        return {"events": []}
    uid = bid["bot_id"]
    # As a replacement/addition to webhooks, we have API events as well to allow you to quickly get old and new events with their epoch
    if event_id is not None:
        api_data = await db.fetchrow("SELECT id, events FROM bot_api_event WHERE bot_id = $1 AND id = $2", uid, event_id)
        if api_data is None:
            return {"events": []}
        event = api_data["events"]
        return {"events": [{"id": uid,  "event": event[0], "epoch": event[1], "context": event[2]}]}

    api_data = await db.fetch("SELECT id, events FROM bot_api_event WHERE bot_id = $1 ORDER BY id", uid)
    if api_data == []:
        return {"events": []}
    events = []
    for _event in api_data:
        event = _event["events"]
        uid = _event["id"]
        events.append({"id": uid,  "event": event[0], "epoch": event[1], "context": orjson.loads(event[2])})
    ret = {"events": events}
    return ret

async def add_event(bot_id: int, event: str, context: dict, *, send_event = True):
    if type(context) == dict:
        pass
    else:
        raise TypeError("Event must be a dict")

    new_event_data = [event, str(time.time()), orjson.dumps(context).decode()]
    id = uuid.uuid4()
    apitok = await db.fetchrow("SELECT api_token FROM bots WHERE bot_id = $1", bot_id)
    if apitok is None:
        return
    asyncio.create_task(db.execute("INSERT INTO bot_api_event (id, bot_id, events) VALUES ($1, $2, $3)", id, bot_id, new_event_data))
    webh = await db.fetchrow("SELECT webhook, webhook_type FROM bots WHERE bot_id = $1", int(bot_id))
    if webh is not None and webh["webhook"] not in ["", None] and webh["webhook_type"] is not None and send_event:
        uri = webh["webhook"]
        cont = True
        if webh["webhook_type"].upper() == "FC":
            f = requests.post
            json = {"event": event, "context": context, "bot_id": str(bot_id), "event_id": str(id)}
            headers = {"Authorization": apitok["api_token"]}
        elif webh["webhook_type"].upper() == "DISCORD" and event in "vote":
            webhook = DiscordWebhook(url=uri)
            user = await get_user(int(context["user_id"])) # Get the user
            bot = await get_bot(bot_id) # Get the bot
            embed = DiscordEmbed(
                title = "New Vote on Fates List",
                description=f"{user['username']} has just cast a vote for {bot['username']} on Fates List!\nIt now has {context['votes']} votes!\n\nThank you for supporting this bot\n**GG**",
                color=242424
            )
            webhook.add_embed(embed)
            response = webhook.execute()
            cont = False
        elif webh["webhook_type"].upper() == "VOTE" and event == "vote":
            f = requests.post
            json = {"id": str(context["user_id"]), "votes": context["votes"]}
            headers = {"Authorization": apitok["api_token"]}
        else:
            cont = False
        if cont:
            print(f"Method Given: {webh['webhook_type'].upper()}")
            print(f"JSON: {json}\nFunction: {f}\nURL: {uri}\nHeaders: {headers}")
            json = json | {"payload": "event", "mode": webh["webhook_type"].upper()}
            asyncio.create_task(f(uri, json = json, headers = headers))
    asyncio.create_task(add_ws_event(bot_id, {"payload": "event", "id": str(id), "event": event, "context": context}))
    return id