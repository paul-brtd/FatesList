from typing import List, Dict, Optional, ForwardRef
from pydantic import BaseModel
import uuid
from aenum import Enum, IntEnum

class UserState(IntEnum):
    _init_ = 'value __doc__'
    normal = 0, "Normal"
    global_ban = 1, "Global Ban"
    login_ban = 2, "Login Ban"
    pedit_ban = 3, "Profile Edit Ban"
    ddr_ban = 4, "Data Deletion Request Ban"

class Status(IntEnum):
    """
    Status object (See https://docs.fateslist.xyz/basics/basic-structures#status for more information)
    """
    _init_ = 'value __doc__'
    unknown = 0, "Unknown"
    online = 1, "Online"
    offline = 2, "Offline"
    idle = 3, "Idle"
    dnd = 4, "Do Not Disturb"

class BotState(IntEnum):
    _init_ = 'value __doc__'
    approved = 0, "Verified"
    pending = 1, "Pending Verification"
    denied = 2, "Denied"
    hidden = 3, "Hidden"
    banned = 4, "Banned"
    under_review = 5, "Under Review"
    certified = 6, "Certified"

class LongDescType(IntEnum):
    _init_ = 'value __doc__'
    html = 0, "HTML/Raw Description"
    markdown_pymarkdown = 1, "Markdown using Python Markdown"
    markdown_marked = 2, "Markdown using JavaScript Marked"

class Vanity(IntEnum):
    _init_ = "value __doc__"
    server = 0, "Server"
    bot = 1, "Bot"
    profile = 2, "Profile"
