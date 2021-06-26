from pydantic import BaseModel
from modules.core.cache import get_any
from asyncpg import Pool
from discord import Client

class DiscordUser():
    def __init__(self, id: int, db: Pool, client: Client):
        self.id = id
        self.db = db
        self.client = client

    # TODO: Is this the best way to do this
    async def fetch(self):
        """Generic method to fetch a user"""
        return await get_any(self.id)
