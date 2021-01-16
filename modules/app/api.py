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
            return "There are no events available right now for you."
        event = api_data["events"]
        return {"id": uid,  "event": event.split("|")[0], "epoch": event.split("|")[1], "context": event.split("|")[2]}

    api_data = await db.fetch("SELECT id, events FROM api_event WHERE bot_id = $1", uid)
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
async def delete_api_events(event: EventDelete):
    """Deletes an event for a bot or deletes all events from a bot (WARNING: DO NOT DO THIS UNLESS YOU KNOW WHAT YOU ARE DOING). Events can be used to set guild/shard counts, enter maintenance mode or to show promotions

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Event ID**: This is the ID of the event you wish to delete. Not passing this will delete ALL events, so be careful
    """
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", event.api_token)
    if id is None:
        return {"done":  False, "reason": "NO_AUTH"}
    id = id["bot_id"]
    if event.event_id is not None:
        await db.execute("DELETE FROM api_event WHERE bot_id = $1 AND id = $2", id, event.event_id)
    else:
        await db.execute("DELETE FROM api_event WHERE bot_id = $1", id)
    return {"done":  True, "reason": None}

@router.patch("/events")
async def create_api_event(event: EventNew):
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

    if event.event.replace(" ", "") in ["add_bot", "edit_bot", "vote"]:
        return {"done":  False, "reason": "INVALID_EVENT_NAME"}
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", event.api_token)
    if id is None:
        return {"done":  False, "reason": "NO_AUTH"}
    id = id["bot_id"]
    await add_event(id, event.event, event.context)
    return {"done":  True, "reason": None}

class EventPatch(BaseModel):
    event_id: uuid.UUID

@router.patch("/test_webhook_broken")
async def test_webhook(request: Request, event: EventPatch):
    print("Event ID = " + str(event.event_id))
    event = await requests.get("http://127.0.0.1:1000/api/events?api_token=DCUaswGL6wmGskYFlVpLbIX6RcjPvnlCkzCkTPI0WiQZoqLGLjDdETA1U6gsS6tK&id=" + str(event.event_id))
    event = await event.json()
    print('Event Type = ' + event['event']) # Vote in most cases
    print('Voter: ' + event['context'].split('::')[0].split("=")[1])
    print('Votes: ' + event['context'].split('::')[1].split("=")[1])

