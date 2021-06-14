from pydantic import BaseModel
import modules.models.enums as enums
from ..base_models import BaseUser, APIResponse
from typing import Optional, List
import uuid

class Login(BaseModel):
    code: str
    scopes: List[str]
    redirect: str
