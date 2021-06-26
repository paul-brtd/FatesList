from pydantic import BaseModel
from typing import Optional, List

class ProfileBot(BaseModel):
    pass

class Profile(BaseModel):
    bots: List[ProfileBot]
    
