from pydantic import BaseModel, validator
import modules.models.enums as enums
from ..base_models import BaseUser, APIResponse
from typing import Optional, List
import uuid

class BotPromotionDelete(BaseModel):
    """Represents a promotion delete request. Your library should internally be using this but you shouldn't need to handle this yourself """
    id: Optional[uuid.UUID] = None

class BotPromotionPartial(BaseModel):
    """
    Represents a partial bot promotion for creating promotions on Fates List
    A partial promotion is similar to a regular promotion object but does not have an id
    """
    title: str
    info: str
    css: Optional[str] = None
    type: int
    
    @validator("title")
    def title_length(cls, v, values, **kwargs):
        if len(v) <= 5:
            raise ValueError('Promotion title must be more than 5 characters')
        return v

class BotPromotion(BotPromotionPartial):
    """
    Represents a bot promotion on Fates List
    A partial promotion is similar to a regular promotion object but does not have an id
    """
    id: uuid.UUID

#LIBRARY-INTERNAL
class BotPromotionList(BaseModel):
    """This is a list of bot promotions. This should be handled by your library """
    __root__: List[BotPromotion]

#LIBRARY-INTERNAL
class BotPromotions(BaseModel):
    """Represents a bot promotion response model. This should be handled by your library"""
    promotions: BotPromotionList
