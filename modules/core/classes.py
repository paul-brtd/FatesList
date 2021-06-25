# Work in progress partial rewrite of Fates List
from pydantic import BaseModel
from .cache import get_bot, get_user, get_any

class DiscordUser(BaseModel):
    id: int
    
    async def fetch(self):
        return await get_any(self.id)
