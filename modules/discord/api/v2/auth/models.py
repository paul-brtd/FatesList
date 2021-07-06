import uuid
from typing import List, Optional, Union

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import AccessToken, APIResponse, BaseUser


class Callback(BaseModel):
    name: str
    url: str
      
class Login(BaseModel):
    code: str
    state: str
        
class LoginInfo(BaseModel):
    scopes: List[str]
    redirect: Optional[str] = "/"
    callback: Callback
 
class OAuthInfo(APIResponse):
    url: Optional[str] = "/"

class LoginBan(BaseModel):
    type: str
    desc: str

class LoginResponse(APIResponse):
    user: BaseUser = BaseUser(
        id = "0", 
        username = "Unknown", 
        avatar = "Unknown", 
        disc = "0000", 
        status = 0, 
        bot = False
    )
    ban: LoginBan = LoginBan(type = "Unknown", desc = "Unknown Ban Type")
    banned: bool = False
    token: str = None
    css: Union[str, None] = None
    state: enums.UserState = None
    js_allowed: bool = False
    access_token: AccessToken = AccessToken(access_token = "", refresh_token = "", expires_in = 0, current_time = 0)
    redirect: str = "/"
