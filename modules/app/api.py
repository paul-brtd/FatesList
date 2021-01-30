from ..deps import *
from uuid import UUID
from fastapi.responses import HTMLResponse
from typing import List

router = APIRouter(
    prefix = "/api",
    include_in_schema = True
)

class EventDelete(BaseModel):
    api_token: str
    event_id: Optional[uuid.UUID] = None

class EventNew(BaseModel):
    api_token: str
    event: str
    context: Optional[str] = "NONE"

class EventUpdate(BaseModel):
    api_token: str
    event_id: uuid.UUID
    event: str
    context: Optional[str] = "NONE"

class TokenRegen(BaseModel):
    api_token: str

class Events(BaseModel):
    events: List[Optional[dict]] = []
    maint: Optional[list] = None
    guild_count: Optional[int] = None

@router.get("/events", tags = ["Events API"], response_model = Events)
async def get_api_events(request: Request, api_token: str, human: Optional[int] = 0, id: Optional[uuid.UUID] = None):
    """
       Gets a list of all events (or just a single event if id is specified. Events can be used to set guild/shard counts, enter maintenance mode or to show promotions

        **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb 

        **Human**: Whether the APIWeb HTML should be returned or the raw JSON. Use 0 unless you are developing APIWeb

        **ID**: The Event UUID if you want to just return a specific event
    """
    ret = await get_events(api_token = api_token, event_id = id)
    if human == 0:
        return ret
    return templates.TemplateResponse("api_event.html", {"request": request, "username": request.session.get("username", False), "avatar": request.session.get("avatar"), "api_token": api_token, "bot_id": bid["bot_id"], "api_response": ret}) 

@router.delete("/events", tags = ["Events API"])
async def delete_api_events(request: Request, event: EventDelete):
    """Deletes an event for a bot or deletes all events from a bot (WARNING: DO NOT DO THIS UNLESS YOU KNOW WHAT YOU ARE DOING). Events can be used to set guild/shard counts, enter maintenance mode or to show promotions

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Event ID**: This is the ID of the event you wish to delete. Not passing this will delete ALL events, so be careful
    """
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", event.api_token)
    if id is None:
        return {"done":  False, "reason": "NO_AUTH"}
    id = id["bot_id"]
    if event.event_id is not None:
        eid = await db.fetchrow("SELECT id FROM api_event WHERE id = $1", event.event_id)
        if eid is None:
            return {"done":  False, "reason": "NO_MESSAGE_FOUND"}
        await db.execute("DELETE FROM api_event WHERE bot_id = $1 AND id = $2", id, event.event_id)
        webh_data = event.event_id
    else:
        await db.execute("DELETE FROM api_event WHERE bot_id = $1", id)
        webh_data = "ALL"

    webh = await db.fetchrow("SELECT webhook FROM bots WHERE bot_id = $1", int(id))
    if webh is not None and webh["webhook"] not in ["", None] and webh["webhook"].startswith("http"):
        try:
            asyncio.create_task(requests.put(webh["webhook"], json = {"type": "delete", "events": webh_data}))
        except:
            pass
    return {"done":  True, "reason": None}

@router.put("/events", tags = ["Events API"])
async def create_api_event(request: Request, event: EventNew):
    """Creates an event for a bot. Events can be used to set guild/shard counts, enter maintenance mode or to show promotions

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Event**: This is the name of the event in question. There are a few special events as well:

        - add_bot - This is an Add Bot Event. These cannot be created normally using the API

        - edit_bot - This is an Edit Bot Event. These cannot be created normally using the API

        - guild_count - Sets the guild count, put the number of guilds in the context field

        - shard_count - Sets the shard count, put the number of shards in the context field

        - vote - This is a vote. These cannot be manually created using the API

        - begin_maint - Enter maintenance mode. Put the reason in the context field

        - end_maint - End Maintenance. Context field is optional here and doesn't matter

        - delete_bot - This is an Delete Bot Event. These cannot be created normally using the API

        - approve - This is an Approve Bot Event. These cannot be created normally using the API

        - deny - This is an Deny Bot Event. These cannot be created normally using the API

    **Note**: All other event names will be shown on the bot's page. You can add css by adding ::css=<YOUR CSS HERE> to the context field but this is not recommended unless you know what you are doing

    **Context**: In a normal event, the context is what will displayed on the body of the event on the bot's page. In a special event, the context usually contains special information about the event in question.
    """

    if len(event.event) < 3:
        return {"done":  False, "reason": "TEXT_TOO_SMALL"}
    if event.event.replace(" ", "") in ["guild_count", "shard_count"] and event.context is None:
        return {"done":  False, "reason": "NO_GUILDS_OR_SHARDS"}
    if event.event.replace(" ", "") in ["add_bot", "edit_bot", "vote", "delete_bot", "approve", "deny"]:
        return {"done":  False, "reason": "INVALID_EVENT_NAME"}
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", event.api_token)
    if id is None:
        return {"done":  False, "reason": "NO_AUTH"}
    id = id["bot_id"]
    await add_event(id, event.event, event.context)
    return {"done":  True, "reason": None}

@router.patch("/events", tags = ["Events API"])
async def edit_api_event(request: Request, event: EventUpdate):
    """Edits an event for a bot given its event ID. Events can be used to set guild/shard counts, enter maintenance mode or to show promotions.

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Event ID**: This is the ID of the event you wish to edit 

    **Event**: This is the new name of the event in question. There are a few special events as well. None of these special events are allowed to be editted or editted to:

        - add_bot

        - edit_bot

        - vote

        - begin_maint

        - end_maint

        - delete_bot

        - approve

        - deny

    **Context**: In a normal event, the context is what will displayed on the body of the event on the bot's page. In a special event, the context usually contains special information about the event in question. You cannot edit the context (or anything for that matter) of a special event
    """
    if len(event.event) < 3:
        return {"done":  False, "reason": "TEXT_TOO_SMALL"}
    if event.event.replace(" ", "") in ["guild_count", "shard_count"] and event.context is None:
        return {"done":  False, "reason": "NO_GUILDS_OR_SHARDS"}
    if event.event.replace(" ", "") in ["add_bot", "edit_bot", "vote", "guild_count", "shard_count", "begin_maint", "end_maint", "delete_bot", "approve", "deny"]:
        return {"done":  False, "reason": "INVALID_EVENT_NAME"}
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", event.api_token)
    if id is None:
        return {"done":  False, "reason": "NO_AUTH"}
    id = id["bot_id"]
    eid = await db.fetchrow("SELECT id, events FROM api_event WHERE id = $1", event.event_id)
    if eid is None:
        return {"done":  False, "reason": "NO_MESSAGE_FOUND"}
    if eid["events"].split("|")[0].replace(" ", "") in ["add_bot", "edit_bot", "vote", "guild_count", "shard_count", "begin_maint", "end_maint", "delete_bot", "approve", "deny"]:
        return {"done":  False, "reason": "INVALID_EVENT_NAME"}
    new_event_data = "|".join((event.event, str(time.time()), event.context))
    await db.execute("UPDATE api_event SET events = $1 WHERE id = $2", new_event_data, event.event_id)
    webh = await db.fetchrow("SELECT webhook FROM bots WHERE bot_id = $1", int(id))
    if webh is not None and webh["webhook"] not in ["", None] and webh["webhook"].startswith("http"):
        try:
            asyncio.create_task(requests.put(webh["webhook"], json = {"type": "update", "event_id": str(event.event_id), "event": event.event, "context": event.context}))
        except:
            pass
    return {"done": True, "reason": None}

@router.patch("/token", tags = ["Core API"])
async def regenerate_token(request: Request, token: TokenRegen):
    """Regenerate the API token

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb
    """
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", token.api_token)
    if id is None:
        return {"done":  False, "reason": "NO_AUTH"}
    await db.execute("UPDATE bots SET api_token = $1 WHERE bot_id = $2", get_token(101), id["bot_id"])
    return {"done": True, "reason": None}


@router.get("/bots/{bot_id}", tags = ["Core API"])
async def get_bots_api(request: Request, bot_id: int):
    """Gets bot information given a bot ID. If not found, 404 will be returned"""
    api_ret = await db.fetchrow("SELECT bot_id AS id, description, tags, long_description, servers AS server_count, shard_count, prefix, invite, owner, extra_owners, bot_library AS library, queue, banned, website, discord AS support, github FROM bots WHERE bot_id = $1", bot_id)
    if api_ret is None:
        return abort(404)
    api_ret = dict(api_ret)
    bot_obj = await get_bot(bot_id)
    api_ret["username"] = bot_obj["username"]
    api_ret["avatar"] = bot_obj["avatar"]
    api_ret["owners"] = [api_ret["owner"]] + api_ret["extra_owners"]
    api_ret["id"] = str(api_ret["id"])
    api_ret["events"] = await get_normal_events(bot_id = bot_id)
    api_ret["maint"] = await in_maint(bot_id = bot_id)
    return api_ret

class APISGC(BaseModel):
    api_token: Optional[str] = None
    guild_count: int
    shard_count: int

@router.post("/bots/stats", tags = ["API Shortcuts"])
async def guild_shard_count_shortcut(request: Request, api: APISGC, Authorization: Optional[str] = FHeader(None)):
    """This is just a shortcut to /api/events for guild/shard posting primarily for BotsBlock but can be used by others. The Swagger Try It Out does not work right now if you use the authorization header but the other api_token in JSON can and should be used instead for ease of use.
    """
    if api.api_token is None and Authorization is None:
        return abort(401)
    elif api.api_token is None:
        atoken = Authorization
    else:
        atoken = api.api_token 
    event = EventNew(api_token = atoken, event = "guild_count", context = str(api.guild_count))
    eve = await create_api_event(request, event)
    if eve["done"] == False and eve["reason"] == "NO_AUTH":
        return abort(401)
    event = EventNew(api_token = atoken, event = "shard_count", context = str(api.shard_count))
    eve = await create_api_event(request, event)
    if eve["done"] == False and eve["reason"] == "NO_AUTH":
        return abort(401)
    return eve

class APISMaint(BaseModel):
    api_token: str
    mode: bool
    reason: Optional[str] = "There was no reason specified"

@router.post("/bots/maint", tags = ["API Shortcuts"])
async def maint_mode_shortcut(request: Request, api: APISMaint):
    """This is just a shortcut to /api/events for enabling or disabling maintenance mode

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Mode**: Whether you went to enter or exit maintenance mode. Setting this to true will enable maintenance and setting this to false will disable maintenance
    """
    if api.mode:
        event_name = "begin_maint"
    else:
        event_name = "end_maint"

    event = EventNew(api_token = api.api_token, event = event_name, context = api.reason)
    eve = await create_api_event(request, event)
    if eve["done"] == False and eve["reason"] == "NO_AUTH":
        return abort(401)
    return eve

async def ws_send_events(websocket):
    for event_i in range(0, len(ws_events)):
        event = ws_events[event_i]
        for ws in manager.active_connections:
            if int(event[0]) in [int(bot_id["bot_id"]) for bot_id in ws.bot_id]:
                rc = await manager.send_personal_message({"msg": "EVENT", "data": event[1], "reason": event[0]}, ws)
                try:
                    if rc != False:
                        ws_events[event_i] = [-1, -2]
                except:
                    pass

async def recv_ws(websocket):
    print("Getting things")
    while True:
        if websocket not in manager.active_connections:
            print("Not connected to websocket")
            return
        print("Waiting for websocket")
        try:
            data = await websocket.receive_json()
            await manager.send_personal_message(data, websocket)
        except WebSocketDisconnect:
            print("Disconnect")
            return
        except:
            continue
        print(data)

@router.websocket("/api/ws")
async def websocker_real_time_api(websocket: WebSocket):
    await manager.connect(websocket)
    if websocket.api_token == []:
        await manager.send_personal_message({"msg": "IDENTITY", "reason": None}, websocket)
        try:
            api_token = await websocket.receive_json()
        except:
            await manager.send_personal_message({"msg": "KILL_CONN", "reason": "NO_AUTH"}, websocket)
            try:
                return await websocket.close(code=4004)
            except:
                return
        api_token = api_token.get("api_token")
        if api_token is None or type(api_token) == int:
            await manager.send_personal_message({"msg": "KILL_CONN", "reason": "NO_AUTH"}, websocket)
            try:
                return await websocket.close(code=4004)
            except:
                return
        for bot in api_token:
            bid = await db.fetchrow("SELECT bot_id, servers FROM bots WHERE api_token = $1", str(bot))
            if bid is None:
                pass
            else:
                websocket.api_token.append(api_token)
                websocket.bot_id.append(bid)
        if websocket.api_token == [] or websocket.bot_id == []:
            await manager.send_personal_message({"msg": "KILL_CONN", "reason": "NO_AUTH"}, websocket)
            return await websocket.close(code=4004)
    await manager.send_personal_message({"msg": "READY", "reason": "AUTH_DONE"}, websocket)
    await ws_send_events(websocket)
    asyncio.create_task(recv_ws(websocket))
    try:
        while True:
            await ws_send_events(websocket)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

