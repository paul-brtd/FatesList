import uuid
from typing import List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser

class BotReview(BaseModel):
    """Note that the reply and id fields are not honored in edit bot"""
    id: Optional[uuid.UUID] = None
    review: str
    star_rating: float
    reply: Optional[bool] = False

    @validator("reply")
    def id_or_no_reply(cls, v, values, **kwargs):
        if v and not id:
            raise ValueError("ID must be provided if reply is set")
        return v
