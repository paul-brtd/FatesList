features = []

import aiohttp
from aiohttp_requests import requests
try:
    import time
    import threading
    from fastapi import FastAPI, APIRouter
    #    import hypercorn
    #    from hypercorn.asyncio import serve
    #    from hypercorn.config import Config
    import uvicorn
    from ws import router
    import asyncio
    import uvloop
    import os
    uvloop.install()
    app = FastAPI()
    features.append("ws")
except:
    pass
try:
    from discord import Client
    features.append("dpy")
except:
    Client = None

import uuid
from typing import Optional

URL = "https://rootspring.loca.lt" # The base fates list site

events_api = URL + "/api/events" 

class InvalidEventName(Exception):
    def __init__(self, name):
        super().__init__(f"Event Name {name} is invalid")

class NetworkError(Exception):
    def __init__(self):
        super().__init__(f"Network Error Or An Internal Server Error Has Occurred")

class AuthFailure(Exception):
    def __init__(self):
        super().__init__(f"Invalid API Token")

class NoGSSource(Exception):
    def __init__(self):
        super().__init__(f"There is no source for guild/shard count. Please either pass in client to FatesClient class or pass in the guild/shard count manually")

class MissingDep(Exception):
    def __init__(self, dep):
        super().__init__(f"Could not start webserver as dependency {dep} is missing")

class FatesClient():
    def __init__(self, *, api_token: str, client: Optional[object] = None):
        self.api_token = api_token
        self.client = client

        if self.client is None:
            self.discord = False
        else:
            self.discord = True
        
        self.features = features
    
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
        if res["done"] == False and res["reason"] == "NO_AUTH":
            raise AuthFailure()
        return res

    async def delete_event(self, *, id: Optional[uuid.UUID] = None):
        if id is None:
            res = await requests.delete(events_api, json = {"api_token": self.api_token})
        else:
            res = await requests.delete(events_api, json = {"api_token": self.api_token, "event_id": str(id)})
        try:
            res = await res.json()        
        except:
            raise NetworkError()
        if res["done"] == False and res["reason"] == "NO_AUTH":
            raise AuthFailure()
        return res

    async def enter_maint_mode(self, reason: Optional[str] = "We are currently undergoing maintenance"):
        return await self.create_event(event = "begin_maint", context = reason)

    async def exit_maint_mode(self):
        return await self.create_event(event = "exit_maint")

    async def set_guild_count(self, count: Optional[int] = None):
        if not self.discord and count is None:
            raise NoGSSource()
        elif count is not None:
            return await self.create_event(event = "guild_count", context = count)
        elif count is None:
            return await self.create_event(event = "guild_count", context = len(client.guilds))

    async def set_shard_count(self, count: Optional[int] = None):
        if not self.discord and count is None:
            raise NoGSSource()
        elif count is not None:
            return await self.create_event(event = "shard_count", context = count)
        elif count is None:
            return await self.create_event(event = "shard_count", context = client.shard_count)

    async def set_guild_shard_count(self, guild_count: Optional[int] = None, shard_count: Optional[int] = None):
        return (await self.set_guild_count(guild_count), await self.set_shard_count(shard_count))


class Event():
    def __init__(self, *, fc: FatesClient, id: uuid.UUID, event: str, context: Optional[str] = None):
        self.id = id
        self.event = event
        if context is not None:
            try:
                self.context = context.split("::css=")[0]
                self.css = context.split("::css=")[1]
            except:
                self.context = context
                self.css = None
        else:
            self.context = None
            self.css = None
        if self.context is not None:
            self.query_args = context.split("::") # These are the context arguments in a list
        else:
            self.query_args = None
        self.fc = fc

    # Simple wrapper for FatesClient.delete_event
    async def delete(self):
       return await self.fc.delete_event(id = self.id) 

    def __repr__(self):
       return f"<APIEvent {str(self.id)}: Event={self.event}, Context={str(self.context)}, CSS={str(self.css)}, Query={str(self.query_args)}>"

    def __str__(self):
        return self.__repr__()

    def __len__(self):
        """Length of an event is how long self.event is"""
        return len(self.event)

    def __eq__(self, other):
        """Two events are equal if their .event property is equal"""
        return (type(other) == Event and self.id == other.id and self.event == other.event and self.context == other.context and self.css == other.css and self.query_args == other.query_args)

class Vote(Event):
    """Vote's Context is a bit special being user=UID::votes=NEW_VOTE_AMOUNT"""
    def get_voter(self):
        return self.context.split("::")[0].split("=")[1]
    def get_votes(self):
        return self.context.split("::")[1].split("=")[1]
    def get_voter_votes(self):
        return self.get_voter(), self.get_votes()

# Web Server for webhook
#class FatesHook():
#    def __init__(self, fc: FatesClient):
#        if "ws" not in fc.features:
#            raise MissingDep("FastAPI")

class WsSettings:
    pass

async def start_ws(route, port = 8012):
    print("Here")
    app.include_router(
        router,
        prefix=route,
    )

    server = uvicorn.Server(uvicorn.Config(app, host = "0.0.0.0", port = port))
    await server.serve()
    try:
        os._exit()
    except:
        os._exit(0)
