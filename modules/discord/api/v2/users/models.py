import uuid
from typing import List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser


class UpdateUserPreferences(BaseModel):
    """Setting field to null and/or omitting it means no change to said field"""

    js_allowed: bool | None = None
    reset_token: bool | None = None
    description: str | None = None
    css: str | None = None


class BotMeta(BaseModel):
    """
    Notes:

    - extra_owners must be a list of strings where the strings
    can be made a integer
    """

    prefix: str
    library: str
    invite: str
    website: str | None = None
    description: str
    banner_card: str | None = None
    banner_page: str | None = None
    keep_banner_decor: bool
    # List of strings that can be turned into a integer
    extra_owners: list[str]
    support: str | None = None
    long_description: str
    css: str | None = None
    long_description_type: enums.LongDescType
    nsfw: bool
    donate: str | None = None
    privacy_policy: str | None = None
    github: str | None = None
    webhook_type: int | None = 0
    webhook: str | None = None
    webhook_secret: str | None = None
    vanity: str
    features: list[str] = []
    tags: list[str]

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
