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
    archived = 7, "Archived"

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

class APIEvents(IntEnum):
    """May or may not be in numeric order"""
    _init_ = "value __doc__"
    bot_vote = 0, "Vote Bot Event"
    bot_add = 1, "Bot Add Event"
    bot_edit = 2, "Bot Edit Event"
    bot_delete = 3, "Bot Delete Event"
    bot_claim = 4, "Bot Claim Event"
    bot_approve = 5, "Bot Approve Event"
    bot_deny = 6, "Bot Deny Event"
    bot_ban = 7, "Bot Ban Event"
    bot_unban = 8, "Bot Unban Event"
    bot_requeue = 9, "Bot Requeue Event"
    bot_certify = 10, "Bot Certify Event"
    bot_uncertify = 11, "Bot Uncertify Event"
    bot_transfer = 12, "Bot Ownership Transfer Event"
    bot_hide = 13, "Bot Hide Event" # Whenever someone makes their bot hidden
    bot_archive = 14, "Bot Archive Event" # When someone archives their bot
    bot_unverify = 15, "Bot Unverify Event"
    bot_view = 16, "Bot View Event (Websocket only)" # WS only
    bot_invite = 17, "Bot Invite Event (Websocket only)" # WS only
    review_vote = 30, "Review Vote Event"
    review_add = 31, "Bot Review Add Event"
    review_edit = 32, "Bot Review Edit Event"
    review_delete = 33, "Bot Review Delete Event"
    command_vote = 50, "Bot Command Vote Event"
    command_add = 51, "Bot Command Add Event"
    command_edit = 52, "Bot Command Edit Event"
    command_delete = 53, "Bot Command Delete Event"
    server_vote = 70, "Server Vote Event"
    server_add = 71, "Server Add Event"
    server_edit = 72, "Server Edit Event"
    server_delete = 73, "Server Delete Event"
    server_ban = 74, "Server Ban Event"
    server_hide = 75, "Server Hide Event" # Whenever someone hides their server
    server_archive = 76, "Server Archive Event" # When someone archives their server
