from typing import List, Optional

from pydantic import BaseModel

from ..base_models import BaseUser


class BotListStats(BaseModel):
    uptime: float
    pid: int
    up: bool
    server_uptime: float
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


class BotVanity(BaseModel):
    type: enums.SearchType
    redirect: str


class BotPartial(BaseModel):
    description: str
    guild_count: int
    banner: Optional[str] = None
    state: enums.BotState
    nsfw: bool
    votes: int
    user: BaseUser


class BotPartialList(BaseModel):
    __root__: List[BotPartial]


class BotIndex(BaseModel):
    tags_fixed: FLTags
    top_voted: BotPartialList
    certified_bots: BotPartialList
    new_bots: BotPartialList
