"""
API v2 beta 2

This is part of Fates List. You can use this in any library you wish. For best API compatibility, just plug this directly in your Fates List library. It has no dependencies other than pydantic, typing and uuid (typing and uuid is builtin)

Depends: enums.py
"""

from fastapi import Form as FForm
from typing import Optional, List, Dict
from pydantic import BaseModel
import sys
sys.path.append("modules/models") # Libraries should remove this
import enums # as enums (for libraries)

class BotMeta(BaseModel):
    prefix: str
    library: str
    invite: str
    website: Optional[str] = ""
    description: str
    banner: Optional[str] = ""
    extra_owners: list
    support: Optional[str] = ""
    long_description: str
    css: Optional[str] = ""
    long_description_type: Optional[enums.LongDescType] = enums.LongDescType.html
    nsfw: Optional[bool] = False
    donate: Optional[str] = ""
    privacy_policy: Optional[str] = ""
    github: Optional[str] = ""
    webhook_type: Optional[int] = 0
    webhook: Optional[str] = ""
    webhook_secret: Optional[str] = ""
    vanity: Optional[str] = ""
    features: Optional[list] = []
    tags: list
    access_token: str
