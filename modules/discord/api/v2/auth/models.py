from pydantic import BaseModel, validator
import modules.models.enums as enums
from ..base_models import BaseUser, APIResponse, AccessToken
from typing import Optional, List, Union
import uuid

class Callback(BaseModel):
    key: str
    verify_key: str
    name: str
    url: str

class BaseLoginInfo(BaseModel):
    scopes: List[str]
    redirect: Optional[str] = "/"

class Login(BaseLoginInfo):
    """Code must be used normally. 
    Access token is only if bb_key matches and the user token you will get in the case of botblock will be a temp user token limited to add bot and edit bot
    """
    code: str
    bb_key: Optional[str] = None
    access_token: Optional[str] = None
    auth_type: Optional[str] = "full"
    
    @validator("access_token")
    def access_token_bb_check(cls, v, values, **kwargs):
        pass
        
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
