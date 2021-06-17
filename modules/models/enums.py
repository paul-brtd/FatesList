from typing import List, Dict, Optional, ForwardRef
from pydantic import BaseModel
import uuid
from aenum import Enum, IntEnum
from config import *

class PromotionType(IntEnum):
    _init_ = 'value __doc__"
    announcement = 0, "Announcement"
    promotion = 1, "Promotion"
    generic = 2, "Generic"

class KnownClients(Enum):
    _init_ = 'value __key__ __banned__ __verified__ __noprompt__'
    fates_list = "Fates List", client_key_fateslist, False, True, True
    lynx = "Lynx", client_key_lynx, False, False, False
    unknown = "Unknown", None, False, False, False
    
cooldown_buckets = {
    "requeue": 60*0.2,
    "ban": 60*0.3,
    "transfer": 60*0.5,
    "reset": 60*1,
    "lock": 60*2
}

class BotAdminOp(IntEnum):
    """Handles bot admin operations"""
    _init_ = 'value __doc__ __perm__ __reason_needed__ __recursive__ __cooldown__'
    requeue = 0, "Requeue Bot", 3, True, False, "requeue"
    claim = 1, "Claim Bot", 2, False, False, None
    unclaim = 2, "Unclaim Bot", 2, False, False, None
    ban = 3, "Ban Bot", 3, True, False, "ban"
    unban = 4, "Unban Bot", 3, True , False, "ban"
    certify = 5, "Certify Bot", 5, False, False, None
    uncertify = 6, "Uncertify Bot", 5, True, False, None
    approve = 7, "Approve Bot", 2, True, False, None
    deny = 8, "Deny Bot", 2, True, False, None
    unverify = 9, "Unverify Bot", 3, True, False, "ban"
    transfer = 10, "Transfer Bot Ownership", 4, True, False, "transfer"
    root_update = 11, "Root State Update", 5, True, False, "transfer"
    reset_votes = 12, "Reset All Votes", (5, 7), True, True, "reset"
    dummy_recursive = 13, "Dummy Resursive", 2, False, True, None
    dummy_nrecursive = 14, "Dummy Nonrecursive", 2, False, False, None
    staff_lock = 15, "Staff Lock Bot", 4, True, False, None
    staff_unlock = 16, "Staff Unlock Bot", 4, True, False, "lock"
    bot_lock = 17, "Bot Lock", 0, False, False, "lock"
    bot_unlock = 18, "Bot Unlock", 0, False, False, "lock"

class BotLock(IntEnum):
    _init_ = 'value __doc__'
    unlocked = 0, "Bot unlocked for editing"
    locked = 1, "Bot locked for editing"
    locked_staff = 2, "Bot locked by staff"
    locked_staff_spam = 3, "Bot locked by staff due to spamming edits"

class PartnerAdType(Enum):
    _init_ = 'value __doc__'
    server = "server", "Server Ad"
    site = "site", "Site Ad"

    def get_col(self):
        return f"{self.value}_ad" 

class PartnerType(IntEnum):
    _init_ = 'value __doc__'
    bot = 0, "Bot"
    guild = 1, "Guild"

class UserState(IntEnum):
    _init_ = 'value __doc__ __sitelock__'
    normal = 0, "Normal (No Ban)", False
    global_ban = 1, "Global Ban", True
    pedit_ban = 2, "Profile Edit Ban", False
    ddr_ban = 3, "Data Deletion Request Ban", True

class BotRequeue(IntEnum):
    _init_ = 'value __doc__'
    claim = 0, "Claim Bot"
    requeue = 1, "Requeue Bot"
    unclaim = 2, "Unclaim Bot"

class WebhookType(IntEnum):
    _init_ = 'value __doc__'
    vote = 0, "Vote Webhook"
    discord = 1, "Discord Integration"
    fc = 2, "Fates Client"

class WebhookResolver(IntEnum):
    _init_ = 'value __doc__'
    not_ack = 0, "Not Acknowledged"
    error = 1, "Post Error"
    posted = 2, "Posted"

class Status(IntEnum):
    """Status object (See https://docs.fateslist.xyz/basics/basic-structures#status for more information)"""
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

class CommandType(IntEnum):
    _init_ = "value __doc__"
    regular = 0, "Regular Command"
    guild_slash = 1, "Slash Command (guild)"
    global_slash = 2, "Slash Command (global)"

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
    bot_unclaim = 18, "Bot Unclaim Event"
    bot_root_update = 19, "Bot Root State Update Event" # Whenever a head admin+ performs a Root State Update on a bot
    bot_vote_reset = 20, "Bot Votes Reset Event" # Whenever all votes for a particular bot either to prevent abuse or otherwise is reset
    bot_vote_reset_all = 21, "Bot Votes Reset All Event" # Whenever all votes are reset, this is usually every month but may not be
    bot_lock = 22, "Bot Lock Event"
    bot_unlock = 23, "Bot Unlock Event"
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
    ws_identity = 90, "Websocket Identity Event"
    ws_identity_res = 91, "Websocket Identity Response Event"
    ws_kill = 92, "Websocket Kill Event"
    ws_status = 93, "Websocket Status Event"
    ws_event = 94, "Websocket Event"
    vote_reminder = 110, "Vote Reminder"

class APIEventTypes(IntEnum):
    _init_ = "value __doc__"
    ws_invalid = 0, "Websocket Invalid Response"
    ws_no_auth = 1, "Websocket No Authentication"
    ws_ready = 3, "Websocket Ready"
    ws_event_single = 4, "Single Websocket Event"
    ws_event_multi = 5, "Mutliple Websocket Events"
    auth_token = 20, "Token Auth"
    auth_manager_key = 21, "Manager Auth"
    vote_webhook = 40, "Vote Webhook Event"

class ObjTypes(IntEnum):
    _init_ = "value __doc__"
    bot = 0, "Bot"
    server = 1, "Server"
