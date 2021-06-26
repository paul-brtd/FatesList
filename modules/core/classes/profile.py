from pydantic import BaseModel
from typing import Optional, List
import modules.models.enums as enums
from .badge import Badge

class ProfileBot(BaseModel):
    bot_id: int
    description: str
    invite: str
    prefix: str
    banner: str
    state: enums.BotState
    votes: int
    guild_count: int
    nsfw: bool       
  
class ProfileData(BaseModel):
    badges: List[Badge]
    description: Optional[str] = "This user prefers to be a enigma"
    css: Optional[str] = None
    js_allowed: bool
    bot_dev: bool
    cert_dev: bool
    state: enums.UserState

class Profile(BaseModel):
    bots: List[ProfileBot]
    approved_bots: List[ProfileBot]
    certified_bots: List[ProfileBot]
    profile: ProfileData
    dup: bool
