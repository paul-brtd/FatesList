import uuid
from typing import List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser

class UpdateUserPreferences(BaseModel):
    """Setting field to null and/or omitting it means no change to said field"""
    js_allowed: Optional[bool] = None
    reset_token: Optional[bool] = None
    description: Optional[str] = None
    css: Optional[str] = None
        
class BotMeta(BaseModel):
    """
    Notes:

    - extra_owners must be a list of strings where the strings
    can be made a integer
    """
    prefix: str
    library: str
    invite: str
    website: Optional[str] = None
    description: str
    banner_card: Optional[str] = None
    banner_page: Optional[str] = None
    keep_banner_decor: bool
    extra_owners: List[str] # List of strings that can be turned into a integer
    support: Optional[str] = None
    long_description: str
    css: Optional[str] = None
    long_description_type: enums.LongDescType
    nsfw: bool
    donate: Optional[str] = None
    privacy_policy: Optional[str] = None
    github: Optional[str] = None
    webhook_type: Optional[int] = 0
    webhook: Optional[str] = None
    webhook_secret: Optional[str] = None
    vanity: str
    features: List[str] = []
    tags: List[str]

    @staticmethod
    @validator("extra_owners")
    def extra_owner_converter(cls, v, values, **kwargs):
        eos = []
        [eos.append(int(eo)) for eo in v if eo.isdigit() and eo not in eos]
        return eos

class OwnershipTransfer(BaseModel):
    new_owner: str

    @staticmethod
    @validator("new_owner")
    def new_owner_validator(cls, v, values, **kwargs):
        try:
            new_owner = str(v)
        except:
            raise ValueError("Invalid new owner")
        return new_owner

class BotAppeal(BaseModel):
    appeal: str

