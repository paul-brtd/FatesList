import uuid
from typing import List, Optional, Dict
import datetime

from pydantic import BaseModel

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser

class GCVFormat(BaseModel):
    """Represents a formatted for client data"""
    guild_count: str
    votes: str

class GuildRandom(BaseModel):
    """
    Represents a random server/guild on Fates List
    """
    guild_id: str
    description: str
    banner_card: Optional[str] = None
    state: int
    username: str
    avatar: str
    guild_count: int
    votes: int
    formatted: GCVFormat

class Guild(BaseModel):
    """
    Represents a server/guild on Fates List
    """
    invite_channel: str
    user: Optional[BaseUser] = None
    description: Optional[str] = None
    tags: List[Dict[str, str]]
    long_description_type: Optional[enums.LongDescType] = None
    long_description: Optional[str] = None
    guild_count: int
    invite_amount: int
    state: enums.BotState
    website: Optional[str] = None
    css: Optional[str] = None
    votes: int
    vanity: str
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
