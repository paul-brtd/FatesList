import uuid
from typing import List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser


class BotPromotion(BaseModel):
    """Reperesents a bots promotion"""
    title: str
    info: str
    css: Optional[str] = None
    type: enums.PromotionType
    
    @staticmethod
    @validator("title")
    def title_length(cls, v, values, **kwargs):
        if len(v) <= 5:
            raise ValueError('Promotion title must be more than 5 characters')
        return v

#LIBRARY-INTERNAL
class BotPromotionList(BaseModel):
    """This is a list of bot promotions. This should be handled by your library """
    __root__: List[BotPromotion]

#LIBRARY-INTERNAL
class BotPromotions(BaseModel):
    """Represents a bot promotion response model. This should be handled by your library"""
    promotions: BotPromotionList
