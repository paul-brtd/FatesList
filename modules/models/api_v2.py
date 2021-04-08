"""
API v2 beta 2

This is part of Fates List. You can use this in any library you wish. For best API compatibility, just plug this directly in your Fates List library. It has no dependencies other than pydantic, typing and uuid (typing and uuid is builtin)
"""

from typing import List, Dict, Optional, ForwardRef
from pydantic import BaseModel
import uuid

class BaseUser(BaseModel):
    """
    Represents a base user class on Fates List.
    """
    id: str
    username: str
    avatar: str
    disc: str
    status: int
    bot: bool

    def __str__(self):
        """
        :return: Returns the username
        :rtype: str
        """
        return self.username

    def get_status(self):
        """
        :return: Returns a status object for the bot
        :rtype: Status
        """
        return Status(status = self.status)

#LIBRARY-INTERNAL
class BotPromotionDelete(BaseModel):
    """
    Represents a promotion delete request. Your library should internally be using this but you shouldn't need to handle this yourself 
    """
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

class BotPromotion(BotPromotionPartial):
    """
    Represents a bot promotion on Fates List

    A partial promotion is similar to a regular promotion object but does not have an id
    """
    id: uuid.UUID

#LIBRARY-INTERNAL
class BotPromotionList(BaseModel):
    """
    This is a list of bot promotions. This should be handled by your library 
    """
    __root__: List[BotPromotion]

#LIBRARY-INTERNAL
class BotPromotionGet(BaseModel):
    """
    Represents a bot promotion response model. This should be handled by your library
    """
    promotions: BotPromotionList

class APIResponse(BaseModel):
    """
    Represents a "regular" API response on Fates List CRUD endpoints

    You can check for success using the done boolean and reason using the reason attribute 
    """
    done: bool
    reason: Optional[str] = None
    code: Optional[int] = None

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
    """
    Represents a list of bot reviews on Fates List
    """
    __root__: List[BotReview]

class BotReviews(BaseModel):
    """
    Represents bot reviews and average stars of a bot on Fates List
    """
    reviews: BotReviewList
    average_stars: float

BotReview.update_forward_refs()
BotReviews.update_forward_refs()

class PrevResponse(BaseModel):
    """
    Represents a response from the Preview API
    """
    html: str

class PrevRequest(BaseModel):
    html_long_description: bool
    data: str

class BotRandom(BaseModel):
    """
    Represents a random bot on Fates List
    """
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
    """
    Represents a bot on Fates List
    """
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
    privacy_policy: Optional[str] = None
    nsfw: bool

class BotPartial(BaseUser):
    description: str
    servers: str
    banner: str
    certified: bool
    bot_id: str
    invite: str
    nsfw: bool

class BotPartialList(BaseModel):
    __root__: List[BotPartial]

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

class AccessToken(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    current_time: str

class ServerList(BaseModel):
    servers: PartialServerDict

class ServerListAuthed(ServerList):
    access_token: AccessToken

class ServerCheck(BaseModel):
    scopes: str
    access_token: AccessToken

class UserDescEdit(BaseModel):
    description: str

class BotReviewVote(BaseModel):
    upvote: bool

class BotPromotion_NotFound(BaseModel):
    detail: str = "Promotion Not Found"
    code: int = 1001

class BotVotesTimestamped(BaseModel):
    timestamped_votes: Dict[str, list]

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
    search_bots: BotPartialList
    profile_search: bool = False

class ProfilePartial(BaseUser):
    description: Optional[str] = None
    banner: None
    certified: Optional[bool] = False

class ProfilePartialList(BaseModel):
    __root__: List[ProfilePartial]

class ProfileSearch(BaseSearch):
    profiles: ProfilePartialList
    profile_search: bool = True

# Data Classes
class Status():
    """
    Represents a status on Fates List
    """
    def __init__(self, status):
        """
        Takes in status as integer and makes a status object
        """
        self.status = status
        
    def __str__(self):
        """
        :return: The status in string form
        :rtype: str
        """
        if self.status == 1:
            return "online"
        elif self.status == 2:
            return "offline"
        elif self.status == 3:
            return "idle"
        elif self.status == 4:
            return "dnd"
        else:
            return "unknown"

