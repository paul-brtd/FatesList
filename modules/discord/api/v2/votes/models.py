from pydantic import BaseModel, validator
import modules.models.enums as enums
from ..base_models import APIResponse
from typing import Optional, List
import uuid

class BotVoteCheck(BaseModel):
    """vts = Vote Timestamps"""
    votes: int
    voted: bool
    vote_right_now: Optional[bool] = None
    vote_epoch: Optional[int] = None
    time_to_vote: Optional[int] = None
    vts: Optional[list] = None
    type: str
    reason: Optional[str] = None
    partial: bool

class BotVote(BaseModel):
    user_id: str
    
    @validator("user_id")
    def userid_int(cls, v, values, **kwargs):
        if not v.isdigit():
            raise ValueError("User ID must be a integer")
        return int(v)
                
