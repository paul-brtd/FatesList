import uuid
from typing import List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser, BasePager

class BotReviewPartial(BaseModel):
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

class BotReview(BaseModel):
    id: uuid.UUID
    reply: bool
    user_id: str
    star_rating: float
    review: str
    review_upvotes: list
    review_downvotes: list
    flagged: bool
    epoch: list
    time_past: str
    user: BaseUser
    replies: Optional[BotReviewList] = []

class BotReviewList(BaseModel):
    """
    Represents a list of bot reviews on Fates List
    """
    __root__: List[BotReview]

BotReviewList = ForwardRef('BotReviewList')       
        
class BotReviews(BaseModel):
    """Represents bot reviews and average stars of a bot on Fates List"""
    reviews: BotReviewList
    average_stars: float
    pager: BasePager

BotReview.update_forward_refs()
BotReviews.update_forward_refs()   
