from typing import List, Dict, Optional, ForwardRef
from pydantic import BaseModel
import uuid
from aenum import Enum, IntEnum

class Status(IntEnum):
    _init_ = 'value __doc__'
    unknown = 0, "Unknown"
    online = 1, "Online"
    offline = 2, "Offline"
    idle = 3, "Idle"
    dnd = 4, "Do Not Disturb"

class BotState(IntEnum):
    _init_ = 'value __doc__'
    verified = 0, "Verified"
    pending = 1, "Pending Verification"
    denied = 2, "Denied"
    hidden = 3, "Hidden"
    banned = 4, "Banned"
