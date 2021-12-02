import uuid
from typing import Optional, Union

from pydantic import BaseModel

from modules.models import enums


class BaseUser(BaseModel):
    """
    Represents a base user class on Fates List.
    """
    id: Optional[str] = "0"
    username: Optional[str] = "Unknown User"
    avatar: Optional[str] = "https://fateslist.xyz/static/botlisticon.webp"
    disc: Optional[str] = "0000"
    status: Optional[enums.Status] = enums.Status.unknown
    bot: Optional[bool] = True

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

        
class BasePager(BaseModel):
    """Information given by the API for pagination"""
    total_count: int
    total_pages: int
    per_page: int
    from_: int
    to: int

    class Config:
        fields = {'from_': 'from'}
