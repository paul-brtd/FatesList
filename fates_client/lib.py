import aiohttp
from aiohttp_requests import requests
from discord import Client
try:
    import fastapi
    ws = True
except:
    ws = False
import uuid
from typing import Optional

URL = "https://firestar.loca.lt" # The base fates list site

events_api = URL + "/api/events" 

class InvalidEventName(Exception):
    def __init__(self, name):
        super().__init__(f"Event Name {name} is invalid")

class NetworkError(Exception):
    def __init__(self):
        super().__init__(f"Network Error Or An Internal Server Error Has Occurred")

class Event():
    def __init__(self, *, id: uuid.UUID, event: str, context: Optional[str] = None):
        self.id = id
        self.event = event
        if context is not None:
            try:
                self.context = context.split("::css=")[0]
                self.css = context.split("::css=")[1]
            except:
                self.context = context
                self.css = None
        self.query_args = context.split("::") # These are the context arguments in a list

class FatesClient():
    def __init__(self, *, api_token: str, client: Client):
        self.api_token = api_token
        self.client = client

    async def create_event(self, *, event: str, context: str = "NONE", css: str = None):
        if event.replace(" ", "") in ["add_bot", "edit_bot", "vote"]:
            raise InvalidEventName(event.replace(" ", ""))
        if type(context) in [list, tuple]:
            context = "::".join(context)
        if css is None:
            pcontext = context
        else:
            pcontext = context + "::css=" + css
        res = await requests.patch(events_api, json = {"api_token": self.api_token, "event": event, "context": pcontext})
        try:
            res = await res.json()
        except:
            raise NetworkError()
        return res

    async def set_guild_count(self):
        return await self.create_event(event = "guild_count", context = len(self.client.guilds))

    async def set_shard_count(self):
        if self.client.shard_count is None:
            return {"done": False, "reason": "NO_SHARDS"}
        return await self.create_event(event = "guild_count", context = self.client.shard_count)

    async def set_guild_shard_count(self):
        return (await self.set_guild_count(), await self.set_shard_count())
