from typing import List, Dict
from modules.imports import *
import uuid

class BaseUser(BaseModel):
    id: str
    username: str
    avatar: str
    disc: str
    status: str

class BotPromotionDelete(BaseModel):
    id: Optional[uuid.UUID] = None

class BotPromotionPartial(BaseModel):
    title: str
    info: str
    css: Optional[str] = None
    type: int

class BotPromotion(BotPromotionPartial):
    id: uuid.UUID

class BotPromotionList(BaseModel):
    __root__: List[BotPromotion]

class BotPromotionGet(BaseModel):
    promotions: BotPromotionList

class APIResponse(BaseModel):
    done: bool
    reason: Optional[str] = None

class BotMaintenancePartial(BaseModel):
    type: int = 1
    reason: Optional[str] = None

class BotMaintenance(BotMaintenancePartial):
    epoch: Optional[str] = None

BotReviewList = ForwardRef('BotReviewList')

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
    __root__: List[BotReview]

class BotReviews(BaseModel):
    reviews: BotReviewList
    average_stars: float

BotReview.update_forward_refs()
BotReviews.update_forward_refs()

class PrevResponse(BaseModel):
    html: str

class PrevRequest(BaseModel):
    html_long_description: bool
    data: str

class RandomBotsAPI(BaseModel):
    bot_id: str
    description: str
    banner: str
    certified: bool
    username: str
    avatar: str
    servers: str
    invite: str
    votes: int

class Bot(BaseUser):
    description: str
    tags: list
    html_long_description: bool
    long_description: Optional[str] = None
    server_count: int
    shard_count: Optional[int] = 0
    user_count: int
    shards: Optional[list] = []
    prefix: str
    library: str
    invite: str
    invite_amount: int
    main_owner: str
    extra_owners: list
    owners: list
    features: list
    queue: bool
    banned: bool
    certified: bool
    website: Optional[str] = None
    support: Optional[str] = None
    github: Optional[str] = None
    css: Optional[str] = None
    votes: int
    vanity: Optional[str] = None
    sensitive: dict
    donate: Optional[str] = None

class BotCommand(BaseModel):
    id: uuid.UUID
    slash: int # 0 = no, 1 = guild, 2 = global
    name: str
    description: str
    args: Optional[list] = ["<user>"]
    examples: Optional[list] = []
    premium_only: Optional[bool] = False
    notes: Optional[list] = []
    doc_link: str

class BotCommandAdd(BaseModel):
    slash: int # 0 = no, 1 = guild, 2 = global
    name: str
    description: str
    args: Optional[list] = ["<user>"]
    examples: Optional[list] = []
    premium_only: Optional[bool] = False
    notes: Optional[list] = []
    doc_link: str

class BotCommandAddResponse(APIResponse):
    id: uuid.UUID

class BotCommands(BaseModel):
    __root__: Dict[uuid.UUID, BotCommand]

class BotCommandEdit(BaseModel):
    id: uuid.UUID
    slash: Optional[int] = None # 0 = no, 1 = guild, 2 = global
    name: Optional[str] = None
    description: Optional[str] = None
    args: Optional[list] = None
    examples: Optional[list] = None
    premium_only: Optional[bool] = None
    notes: Optional[list] = None
    doc_link: Optional[str] = None

class BotCommandDelete(BaseModel):
    id: uuid.UUID

class BotVoteCheck(BaseModel):
    votes: int
    voted: bool
    vote_right_now: bool
    vote_epoch: int
    time_to_vote: int

class BotStats(BaseModel):
    guild_count: int
    shard_count: Optional[int] = None
    shards: Optional[list] = None
    user_count: Optional[int] = None

class BotVanity(BaseModel):
    type: str
    redirect: str

class User(BaseUser):
    id: str
    description: Optional[str] = None
    css: str

class PartialServer(BaseModel):
    icon: str
    name: str
    member_count: int
    created_at: str
    code: Optional[str] = None # Only in valid_servers

class PartialServerDict(BaseModel):
    __root__: Dict[str, PartialServer]

class ValidServer(BaseModel):
    valid: PartialServerDict

class UserDescEdit(BaseModel):
    description: str

class BotPromotion_NotFound(BaseModel):
    detail: str = "Promotion Not Found"
    code: int = 1001
