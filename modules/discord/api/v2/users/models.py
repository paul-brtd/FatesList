import uuid
from typing import List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser


class BotMeta(BaseModel):
    """
    Notes:

    - extra_owners must be a list of strings where the strings
    can be made a integer
    """
    prefix: str
    library: str
    invite: str
    website: Optional[str] = ""
    description: str
    banner: Optional[str] = ""
    extra_owners: List[str] # Int in reality but JSON
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
    features: Optional[List[str]] = []
    tags: List[str]

    @validator("extra_owners")
    def extra_owner_converter(cls, v, values, **kwargs):
        eos = []
        [eos.append(int(eo)) for eo in v if eo.isdigit() and eo not in eos]
        return eos
