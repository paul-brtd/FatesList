"""
API v2 beta 2

This is part of Fates List. You can use this in any library you wish. For best API compatibility, just plug this directly in your Fates List library. It has no dependencies other than aenum, pydantic, typing and uuid (typing and uuid is builtin)

Depends: enums.py
"""

import sys
import uuid
from typing import Dict, ForwardRef, List, Optional, Union

from pydantic import BaseModel, validator

sys.path.append("modules/models") # Libraries should remove this
import datetime

import enums  # as enums (for libraries)

from .base_models import *

class PrevResponse(BaseModel):
    """
    Represents a response from the Preview API
    """
    html: str

class PrevRequest(BaseModel):
    html_long_description: bool
    data: str

class VoteReminderPatch(BaseModel):
    remind: bool

class BotPartial(BaseUser):
    description: str
    guild_count: str
    banner: Optional[str] = None
    state: enums.BotState
    bot_id: str
    invite: Optional[str] = None
    nsfw: bool
    votes: int

class BotPartialList(BaseModel):
    __root__: List[BotPartial]

class BotVoteCheck(BaseModel):
    votes: int
    voted: bool
    vote_right_now: bool
    vote_epoch: int
    time_to_vote: int

class BotVanity(BaseModel):
    type: str
    redirect: str

class User(BaseUser):
    id: str
    state: enums.UserState
    description: Optional[str] = None
    css: str

class BotReviewAction(BaseModel):
    user_id: str

class BotReviewVote(BotReviewAction):
    upvote: bool

class Timestamp(BaseModel):
    __root__: int

class TimestampList(BaseModel):
    __root__: List[Timestamp]

class BotVotesTimestamped(BaseModel):
    timestamped_votes: Dict[str, TimestampList]

class FLFeature(BaseModel):
    type: str
    description: str

class FLTag(BaseModel):
    name: str
    iconify_data: str
    id: str

class FLTags(BaseModel):
    __root__: List[FLTag]

class BotIndex(BaseModel):
    tags_fixed: FLTags
    top_voted: BotPartialList
    certified_bots: BotPartialList
    new_bots: BotPartialList
    roll_api: str

class BaseSearch(BaseModel):
    tags_fixed: FLTags
    query: str

class BotSearch(BaseSearch):
    search_res: list
    profile_search: bool 

class ProfilePartial(BaseUser):
    description: Optional[str] = None
    banner: Optional[str] = None
    certified: Optional[bool] = False

class ProfilePartialList(BaseModel):
    __root__: List[ProfilePartial]

class ProfileSearch(BaseSearch):
    profiles: ProfilePartialList
    profile_search: bool = True
