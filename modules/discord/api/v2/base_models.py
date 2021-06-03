import modules.models.enums as enums
from pydantic import BaseModel
from typing import Optional
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
    
    Code is mostly random and for debugging other than 1000 and 1001 where 1000 means success and 1001 means success with message
    """
    done: bool
    reason: Optional[str] = None
    code: int = 1000

class IDResponse(APIResponse):
    id: uuid.UUID
