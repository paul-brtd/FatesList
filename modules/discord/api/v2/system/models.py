from typing import List, Optional
from ..base_models import BaseUser
from pydantic import BaseModel


class BotListStats(BaseModel):
    uptime: float
    pid: int
    up: bool
    dup: bool
    bot_count: int
    bot_count_total: int
    workers: Optional[List[int]] = []

class PartialBotQueue(BaseModel):
    user: Optional[BaseUser] = BaseUser()
    prefix: str
    invite: str
    description: str

class BotQueueList(BaseModel):
    __root__: List[PartialBotQueue]

class BotQueueGet(BaseModel):
    bots: Optional[BotQueueList] = None
