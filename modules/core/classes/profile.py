from pydantic import BaseModel
from typing import Optional, List

class ProfileBot(BaseModel):
    bot_id
    description
    prefix
    banner
    state
    votes
    servers
    nsfw 

class Profile(BaseModel):
    bots: List[ProfileBot]
    
