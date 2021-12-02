import datetime
import uuid
from typing import Dict, List, Optional

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

    invite_channel: Optional[str] = None
    user: BaseUser
    description: Optional[str] = None
    tags: List[Dict[str, str]]
    long_description_type: Optional[enums.LongDescType] = None
    long_description: Optional[str] = None
    guild_count: int
    invite_amount: int
    total_votes: int
    user_whitelist: Optional[List[str]] = None
    user_blacklist: Optional[List[str]] = None
    state: enums.BotState
    website: Optional[str] = None
    css: Optional[str] = None
    votes: int
    vanity: str
    nsfw: bool
    banner_card: Optional[str] = None
    banner_page: Optional[str] = None
    keep_banner_decor: Optional[bool] = None
