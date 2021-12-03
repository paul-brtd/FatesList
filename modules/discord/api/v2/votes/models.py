import uuid
from typing import List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse


class BotVoteCheck(BaseModel):
    """vts = Vote Timestamps"""

    votes: int
    voted: bool
    vote_right_now: bool | None = None
    vote_epoch: int | None = None
    time_to_vote: int | None = None
    vts: list | None = None
