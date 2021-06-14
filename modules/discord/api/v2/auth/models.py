from pydantic import BaseModel
import modules.models.enums as enums
from ..base_models import BaseUser, APIResponse
from typing import Optional, List
import uuid

class LoginInfo(BaseModel):
    scopes: List[str]
    redirect: Optional[str] = "/"

class Login(LoginInfo):
    code: str
    oauth_redirect: Optional[str] = None


