import aiohttp
from aiohttp_requests import requests
import uuid

URL = "https://firestar.loca.lt" # The base fates list site

events_api = URL + "/api/events" 

class InvalidEventName(Exception):
    def __init__(self, name):
        super().__init__(f"Event Name {name} is invalid")

class NetworkError(Exception):
    def __init__(self):
        super().__init__(f"Network Error Or An Internal Server Error Has Occurred")

class _Event():
    def __init__(self, *, id: uuid.UUID, event: str = None, context: str = None):
        self.id = id
        self.event = event
        self.context = context

class FatesClient():
    def __init__(self, *, api_token: str):
        self.api_token = api_token

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
