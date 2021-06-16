import modules.models.enums as enums
from pydantic import BaseModel
from typing import Optional, Union
import uuid

class BaseUser(BaseModel):
    """
    Represents a base user class on Fates List.
    """
    id: str
    username: str
    avatar: str
    disc: str
    status: enums.Status
    bot: bool

    def __str__(self):
        """
        :return: Returns the username
        :rtype: str
        """
        return self.username

    def get_status(self):
        """
        :return: Returns a status object for the bot
        :rtype: Status
        """
        return Status(status = self.status)

class APIResponse(BaseModel):
    """
    Represents a "regular" API response on Fates List CRUD endpoints

    You can check for success using the done boolean and reason using the reason attribute 
    
    """
    done: bool
    reason: Optional[str] = None

class IDResponse(APIResponse):
    id: uuid.UUID

class AccessToken(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    current_time: Union[float, int]

