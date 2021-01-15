from ..deps import *

router = APIRouter(
    prefix = "/api",
    tags = ["API"]
)

@router.get("/events")
async def get_api_events(api_token: str):
    bid = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", api_token)
    if bid is None:
        return {"events": []}
    uid = bid["bot_id"]
    # As a replacement/addition to webhooks, we have API events as well to allow you to quickly get old and new events with their epoch
    api_data = await db.fetch("SELECT id, events FROM api_event WHERE bot_id = $1", uid)
    if api_data == []:
        return {"events": []}
    events = []
    for _event in api_data:
        event = _event["events"]
        uid = _event["id"]
        events.append({"id": uid,  "event": event.split("|")[0], "epoch": event.split("|")[1], "context": event.split("|")[2]})
    return {"events": events, "maint": (await in_maint(bid["bot_id"]))}

@router.delete("/events")
async def delete_api_events(api_token: str):
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", api_token)
    if id is None:
        return {"done":  False, "reason": "NO_AUTH"}
    id = id["bot_id"]
    await db.execute("DELETE FROM api_event WHERE bot_id = $1", id)
    return {"done":  True, "reason": None}

@router.put("/events")
async def create_api_event(api_token: str, event: str, context: Optional[str] = "NONE"):
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", api_token)
    if id is None:
        return {"done":  False, "reason": "NO_AUTH"}
    id = id["bot_id"]
    await add_event(id, event, context)
    return {"done":  True, "reason": None}
