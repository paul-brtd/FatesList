import uuid
from typing import List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser

class BotReviewPartial(BaseModel):
    id: Optional[uuid.UUID] = None
    review: str
    star_rating: float
    reply: bool
