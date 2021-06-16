from pydantic import BaseModel
import modules.models.enums as enums
from ..base_models import BaseUser, APIResponse, AccessToken
from typing import Optional, List, Union
import uuid

class Callback(BaseModel):
    key: str
    name: str
    url: str

class BaseLoginInfo(BaseModel):
    scopes: List[str]
    redirect: Optional[str] = "/"

class Login(BaseLoginInfo):
    code: str
        
class LoginInfo(BaseLoginInfo):
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
