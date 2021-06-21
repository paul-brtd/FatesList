from pydantic import BaseModel
import modules.models.enums as enums
from ..base_models import BaseUser, APIResponse
from typing import Optional, List
import uuid

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
    features: Optional[List[str]] = []
    tags: List[str] 
