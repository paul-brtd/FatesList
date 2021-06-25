import uuid
from typing import List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse


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
