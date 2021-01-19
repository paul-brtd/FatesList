from ..deps import *
from uuid import UUID
from fastapi.responses import HTMLResponse

router = APIRouter(
    prefix = "/api",
    tags = ["API"],
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

@router.get("/events")
async def get_api_events(request: Request, api_token: str, human: Optional[int] = 0, id: Optional[uuid.UUID] = None):
    """
       Gets a list of all events (or just a single event if id is specified. Events can be used to set guild/shard counts, enter maintenance mode or to show promotions

        **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb 

        **Human**: Whether the APIWeb HTML should be returned or the raw JSON. Use 0 unless you are developing APIWeb

        **ID**: The Event UUID if you want to just return a specific event
    """
    bid = await db.fetchrow("SELECT bot_id, servers FROM bots WHERE api_token = $1", api_token)
    if bid is None:
        return {"events": []}
    uid = bid["bot_id"]
    # As a replacement/addition to webhooks, we have API events as well to allow you to quickly get old and new events with their epoch
    if id is not None:
        api_data = await db.fetchrow("SELECT id, events FROM api_event WHERE bot_id = $1 AND id = $2", uid, id)
        if api_data is None:
            return {"events": []}
        event = api_data["events"]
        return {"id": uid,  "event": event.split("|")[0], "epoch": event.split("|")[1], "context": event.split("|")[2]}

    api_data = await db.fetch("SELECT id, events FROM api_event WHERE bot_id = $1 ORDER BY id", uid)
    if api_data == []:
        return {"events": []}
    events = []
    for _event in api_data:
        event = _event["events"]
        uid = _event["id"]
        if len(event.split("|")[0]) < 3:
            continue # Event name size is too small
        events.append({"id": uid,  "event": event.split("|")[0], "epoch": event.split("|")[1], "context": event.split("|")[2]})
    ret = {"events": events, "maint": (await in_maint(bid["bot_id"])), "guild_count": bid["servers"]}
    if human == 0:
        return ret
    return templates.TemplateResponse("api_event.html", {"request": request, "username": request.session.get("username", False), "avatar": request.session.get("avatar"), "api_token": api_token, "bot_id": bid["bot_id"], "api_response": ret}) 

@router.delete("/events")
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
            asyncio.create_task(requests.patch(webh["webhook"], json = {"type": "delete", "events": webh_data}))
        except:
            pass
    return {"done":  True, "reason": None}

@router.put("/events")
async def create_api_event(request: Request, event: EventNew):
    """Creates an event for a bot. Events can be used to set guild/shard counts, enter maintenance mode or to show promotions

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Event**: This is the name of the event in question. There are a few special events as well:

        - add_bot - This is an Add Bot Event. These cannot be created using the API

        - edit_bot - This is an Edit Bot Event. These cannot be created using the API

        - guild_count - Sets the guild count, put the number of guilds in the context field

        - shard_count - Sets the shard count, put the number of shards in the context field

        - vote - This is a vote. These cannot be manually created using the API

        - begin_maint - Enter maintenance mode. Put the reason in the context field

        - end_maint - End Maintenance. Context field is optional here and doesn't matter

    **Note**: All other event names will be shown on the bot's page. You can add css by adding ::css=<YOUR CSS HERE> to the context field but this is not recommended unless you know what you are doing

    **Context**: In a normal event, the context is what will displayed on the body of the event on the bot's page. In a special event, the context usually contains special information about the event in question.
    """

    if len(event.event) < 3:
        return {"done":  False, "reason": "TEXT_TOO_SMALL"}
    if event.event.replace(" ", "") in ["guild_count", "shard_count"] and event.context is None:
        return {"done":  False, "reason": "NO_GUILDS_OR_SHARDS"}
    if event.event.replace(" ", "") in ["add_bot", "edit_bot", "vote"]:
        return {"done":  False, "reason": "INVALID_EVENT_NAME"}
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", event.api_token)
    if id is None:
        return {"done":  False, "reason": "NO_AUTH"}
    id = id["bot_id"]
    await add_event(id, event.event, event.context)
    return {"done":  True, "reason": None}

@router.patch("/events")
async def edit_event(request: Request, event: EventUpdate):
    """Edits an event for a bot given its event ID. Events can be used to set guild/shard counts, enter maintenance mode or to show promotions.

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Event ID**: This is the ID of the event you wish to edit 

    **Event**: This is the new name of the event in question. There are a few special events as well. None of these special events are allowed to be editted or editted to:

        - add_bot - This is an Add Bot Event. These cannot be created using the API

        - edit_bot - This is an Edit Bot Event. These cannot be created using the API

        - guild_count - Sets the guild count, put the number of guilds in the context field

        - shard_count - Sets the shard count, put the number of shards in the context field

        - vote - This is a vote. These cannot be manually created using the API

        - begin_maint - Enter maintenance mode. Put the reason in the context field.

        - end_maint - End Maintenance. Context field is optional here and doesn't matter

    **Note**: All other event names will be shown on the bot's page. You can add css by adding ::css=<YOUR CSS HERE> to the context field but this is not recommended unless you know what you are doing

    **Context**: In a normal event, the context is what will displayed on the body of the event on the bot's page. In a special event, the context usually contains special information about the event in question. You cannot edit the context (or anything for that matter) of a special event
    """
    if len(event.event) < 3:
        return {"done":  False, "reason": "TEXT_TOO_SMALL"}
    if event.event.replace(" ", "") in ["guild_count", "shard_count"] and event.context is None:
        return {"done":  False, "reason": "NO_GUILDS_OR_SHARDS"}
    if event.event.replace(" ", "") in ["add_bot", "edit_bot", "vote", "guild_count", "shard_count", "begin_maint", "end_maint"]:
        return {"done":  False, "reason": "INVALID_EVENT_NAME"}
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", event.api_token)
    if id is None:
        return {"done":  False, "reason": "NO_AUTH"}
    id = id["bot_id"]
    eid = await db.fetchrow("SELECT id, events FROM api_event WHERE id = $1", event.event_id)
    if eid is None:
        return {"done":  False, "reason": "NO_MESSAGE_FOUND"}
    if eid["events"].split("|")[0].replace(" ", "") in ["add_bot", "edit_bot", "vote", "guild_count", "shard_count", "begin_maint", "end_maint"]:
        return {"done":  False, "reason": "INVALID_EVENT_NAME"}
    new_event_data = "|".join((event.event, str(time.time()), event.context))
    await db.execute("UPDATE api_event SET events = $1 WHERE id = $2", new_event_data, event.event_id)
    webh = await db.fetchrow("SELECT webhook FROM bots WHERE bot_id = $1", int(id))
    if webh is not None and webh["webhook"] not in ["", None] and webh["webhook"].startswith("http"):
        try:
            asyncio.create_task(requests.patch(webh["webhook"], json = {"type": "update", "event_id": str(event.event_id), "event": event.event, "context": event.context}))
        except:
            pass
    return {"done": True, "reason": None}

@router.patch("/token")
async def regenerate_token(request: Request, token: TokenRegen):
    """Regenerate the API token

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb
    """
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", event.api_token)
    if id is None:
        return {"done":  False, "reason": "NO_AUTH"}
    await db.execute("UPDATE bots SET api_token = $1 WHERE bot_id = $2", get_token(101), id["bot_id"])
    return {"done": True, "reason": None}

