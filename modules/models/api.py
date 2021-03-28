from typing import List, Dict
from modules.imports import *
import uuid

class PromoDelete(BaseModel):
    promo_id: Optional[uuid.UUID] = None

class Promo(BaseModel):
    title: str
    info: str
    css: Optional[str] = None
    type: int

class PromoObj(BaseModel):
    promotions: list

class PromoPatch(Promo):
    promo_id: uuid.UUID

class APIResponse(BaseModel):
    done: bool
    reason: Optional[str] = None

class PartialBotMaint(BaseModel):
    type: int = 1
    reason: Optional[str] = None

class BotMaint(PartialBotMaint):
    epoch: Optional[str] = None

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

class BaseUser(BaseModel):
    id: str
    username: str
    avatar: str
    disc: str
    status: str

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
    reviews: Optional[list] = None # Compact
    sensitive: dict
    promotions: Optional[List[Promo]] = {}
    maintenance: BotMaint
    average_stars: Optional[float] = None # Conpact
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
    description: str
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

