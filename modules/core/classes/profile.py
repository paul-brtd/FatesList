from pydantic import BaseModel
from typing import Optional, List
import modules.models.enums as enums
from .badge import Badge

class ProfileBot(BaseModel):
    """A bot attached to a users profile"""
    bot_id: int
    avatar: str
    description: str
    invite: str
    prefix: str
    banner: str
    state: enums.BotState
    votes: int
    guild_count: int
    nsfw: bool       
  
class ProfileData(BaseModel):
    """Misc data about a user"""
    badges: List[Badge]
    description: Optional[str] = "This user prefers to be a enigma"
    css: Optional[str] = None
    js_allowed: bool
    bot_developer: bool
    certified_developer: bool
    state: enums.UserState

class Profile(BaseModel):
    bots: List[ProfileBot]
    approved_bots: List[ProfileBot]
    certified_bots: List[ProfileBot]
    profile: ProfileData
    user: enums.BaseUser
    dup: bool
    
