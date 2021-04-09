from typing import List, Dict, Optional, ForwardRef
from pydantic import BaseModel
import uuid
from enum import Enum, IntEnum

class Status(IntEnum):
    unknown = 0
    online = 1
    offline = 2
    idle = 3
    dnd = 4

class BotState(IntEnum):
    verified = 0
    pending = 1
    denied = 2
    hidden = 3
    banned = 4
