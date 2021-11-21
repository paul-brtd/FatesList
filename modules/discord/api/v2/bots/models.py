import uuid
from typing import List, Optional
import datetime

from pydantic import BaseModel

from modules.models import enums

from ..base_models import APIResponse, BaseUser

class GCVFormat(BaseModel):
    """Represents a formatted for client data"""
    guild_count: str
    votes: str

class BotRandom(BaseModel):
    """
    Represents a random bot on Fates List
    """
    bot_id: str
    description: str
    banner_card: Optional[str] = None
    state: int
    username: str
    avatar: str
    guild_count: int
    invite: Optional[str] = None
    votes: int
    formatted: GCVFormat

class BotOwner(BaseModel):
    user: BaseUser
    main: bool

class BotOwners(BaseModel):
    __root__: List[BotOwner]
        
class Bot(BaseModel):
    """
    Represents a bot on Fates List
    """
    user: Optional[BaseUser] = None
    description: Optional[str] = None
    tags: List[str]
    last_stats_post: Optional[datetime.datetime] = None
    long_description_type: Optional[enums.LongDescType] = None
    long_description: Optional[str] = None
    guild_count: int
    shard_count: Optional[int] = 0
    user_count: int
    shards: Optional[List[int]] = []
    prefix: str
    library: str
    invite: Optional[str] = None
    invite_link: str
    invite_amount: int
    owners: Optional[BotOwners] = None
    features: List[str]
    state: enums.BotState
    website: Optional[str] = None
    support: Optional[str] = None
    github: Optional[str] = None
    css: Optional[str] = None
    votes: int
    vanity: str
    donate: Optional[str] = None
    privacy_policy: Optional[str] = None
    nsfw: bool
    banner_card: Optional[str] = None
    banner_page: Optional[str] = None
    keep_banner_decor: Optional[bool] = None

class BotStats(BaseModel):
    guild_count: int
    shard_count: Optional[int] = None
    shards: Optional[List[int]] = None
    user_count: Optional[int] = None
        
class BotEvent(BaseModel):
    m: dict
    ctx: dict

class BotEventList(BaseModel):
    __root__: List[BotEvent]

class BotEvents(BaseModel):
    events: BotEventList
