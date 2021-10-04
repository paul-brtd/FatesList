import uuid
from typing import Dict, ForwardRef, List, Optional

from aenum import Enum, IntEnum
from pydantic import BaseModel


class ULAState(IntEnum):
    _init_ = "value __doc__"
    pending = 0, "Pending Verification"
    approved = 1, "Approved"

class ULAMethod(IntEnum):
    _init_ = "value __doc__"
    get = 0, "GET method"
    post = 1, "POST method"
    put = 2, "PUT method"
    patch = 3, "PATCH method"
    delete = 4, "DELETE method"

class ULAFeature(IntEnum):
    _init_ = "value __doc__"
    get_bot = 1, "Get Bot"
    post_stats = 2, "Post Stats"
    get_user_voted = 3, "Get User Voted"
