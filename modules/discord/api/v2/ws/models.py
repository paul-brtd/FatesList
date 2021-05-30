"""
API v2 beta 2

This is part of Fates List. You can use this in any library you wish. For best API compatibility, just plug this directly in your Fates List library. It has no dependencies other than aenum, pydantic, typing and uuid (typing and uuid is builtin)
"""

from pydantic import BaseModel

class WebsocketBootstrap(BaseModel):
    versions: list
    endpoints: dict
