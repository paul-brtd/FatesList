from fastapi import APIRouter
from pydantic import BaseModel
import uuid
from typing import Optional, Union

router = APIRouter()

class EventPatch(BaseModel):
    type: str
    event_id: uuid.UUID
    event: Optional[str] = None
    events: Optional[str] = None
    context: Optional[Union[int, str]] = None

@router.patch("/")
async def fates_hook_webhook(event: EventPatch):
    if event.type != "add" or event.event != fh_cond:
        print("DEBUG: Invalid event gotten")
        return
    if event.event == "vote":
        event = Vote(fc = fc, id = event.event_id, event = event.event, context = event.context)
    else:
        event = Event(fc = fc, id = event.event_id, event = event.event, context = event.context)
    return await fh_func(event)
