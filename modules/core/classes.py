# Work in progress partial rewrite of Fates List
from pydantic import BaseModel
from .cache import get_bot, get_user, get_any

class DiscordUser(BaseModel):
    id: int

    # TODO: Is this the best way to do this
    async def fetch(self):
        """Generic method to fetch a user"""
        return await get_any(self.id)
      
class User(DiscordUser):
    async def fetch(self):
        """Fetch a user object from the discord API"""
        return await get_user(self.id)
