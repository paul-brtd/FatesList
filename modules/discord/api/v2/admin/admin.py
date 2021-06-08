from modules.core import *
from .models import APIResponse, BotQueueGet, BotListPartner, BotListPartnerAd, BotListPartnerChannel, IDResponse, enums, BotAdminOpEndpoint
from modules.discord.admin import admin_dashboard
from ..base import API_VERSION
import uuid
import bleach
from lxml.html.clean import Cleaner

cleaner = Cleaner()

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/admin",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Admin"]
)

class InvalidInvite(Exception):
    pass

@router.get("/console")
async def botlist_admin_console_api(request: Request):
    """API to get raw admin console info"""
    return await admin_dashboard(request) # Just directly render the admin dashboard. It knows what to do

@router.get("/err", response_model = APIResponse)
@router.post("/err", response_model = APIResponse)
async def error_maker(request: Request, test: Optional[APIResponse] = None):
    error = int("haha")

@router.patch("/bots/{bot_id}/ops", response_model = APIResponse)
async def bot_admin_operation(request: Request, bot_id: int, data: BotAdminOpEndpoint, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    """Performs a bot admin operation. This is internal and only meant for our test server manager bot. 0 is the recursion bot for botlist-wide actions like vote resets every month"""
    
    # Manager key check (only redbot can use this api) 
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    
    # Get user
    guild = client.get_guild(main_server)
    if not guild: # Guild is None when still connecting to discord
        return api_error("Not yet connected to discord", 2761, status_code = 503, headers = {"Retry-After": 5})
    user = guild.get_member(data.mod)
    
    # Get permission handling recursive operations, which have a tuple where first element is for non recursive and second is for recursive
    if isinstance(data.op.__perm__, tuple):
        if data.op.__recursive__:
            perm = data.op.__perm__[0] if bot_id != 0 else data.op.__perm__[1]
    else:
        perm = data.op.__perm__
    
    # Check if they are staff or not
    staff = is_staff(staff_roles, user.roles, perm)
    if user is None or not staff[0]:
        return api_error(f"You do not have permission to perform this action! You need permlevel {perm}", 2764, status_code = 403)
    
    # Handle cooldown by first getting the bucket and checking the ttl of the needed key given bucket
    if data.op.__cooldown__:
        bucket_time = enums.cooldown_buckets[data.op.__cooldown__] # Get Bucket
        coolkey = await redis_db.ttl(f"cooldown-{data.op.__cooldown__}-{data.mod}") # Format: cooldown-BUCKET-MOD
        if coolkey not in (-1, -2): # https://redis.io/commands/ttl, -2 means no key found and -1 means key exists but has no associated expire
            return api_error(f"This operation is on cooldown for {coolkey} seconds", 2767, status_code = 429, headers = {"Retry-After": coolkey}) # Ratelimired
        await redis_db.set(f"cooldown-{data.op.__cooldown__}-{data.mod}", 0, ex = int(bucket_time)) # Add ratelimit to user for said bucket and set expiry to ex

    # Check that reason is given where needed
    if data.op.__reason_needed__ and not data.reason:
        return api_error("Please specify a reason for doing this!", 2753)
    
    # Create admin_tool for use by ops
    admin_tool = BotListAdmin(bot_id, data.mod)
    
    # Using Bot ID 0 on a non recursive command is not allowed
    if bot_id == 0 and not data.op.__recursive__:
        return api_error("This operation is not recursive. You must provide a nonzero Bot ID", 2763)
    
    # Check that the state exists and get it too
    state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)
    if state is None:
        return api_error("This bot does not exist", 2747, status_code = 404)
    try:
        state = enums.BotState(state)
    except:
        return api_error("Bot is in invalid state. Contact the developers of this list and ask them to fix this!", 2761)

    state_str = f"(state: {state} -> {state.__doc__})" # State string for some operations. Format: (state: STATE DESCRIPTION)
    
    success_msg = None # Success message, changing this will change the reason key in the success message
    task = False # Whether to run op tasks using asyncio.create_task (True) or await (False)
    success_code = 200 # Status codes to be used on success
    tool = None # Default tool/op to use 
    
    # Claim
    if data.op == enums.BotAdminOp.claim:
        if state == enums.BotState.under_review:
            verifier = await db.fetchval("SELECT verifier FROM bots WHERE bot_id = $1", bot_id)
            return api_error(f"This bot has already been claimed by <@{verifier}> ({verifier})", 2750)

        elif state != enums.BotState.pending:
            return api_error(f"This bot is not currently pending review {state_str}", 2751)
        tool = admin_tool.claim_bot()
        
    # Unclaim
    elif data.op == enums.BotAdminOp.unclaim:
        if state != enums.BotState.under_review:
            return api_error(f"This bot is not currently claimed and hence cannot be unclaimed {state_str}", 2749)
        tool = admin_tool.unclaim_bot()
    
    # Ban
    elif data.op == enums.BotAdminOp.ban:
        if state == enums.BotState.banned:
            return api_error("This bot has already been banned", 2752)
        tool = admin_tool.ban_bot(data.reason)
    
    # Unban
    elif data.op == enums.BotAdminOp.unban:
        if state != enums.BotState.banned:
            return api_error(f"This bot has not been banned {state_str}", 2749)
        tool = admin_tool.unban_bot(data.reason)
        
    # Certify
    elif data.op == enums.BotAdminOp.certify:
         if state == enums.BotState.certified:
             return api_error("Bot is already certified", 2754)
         elif state != enums.BotState.approved:
             return api_error(f"Bot is not in a approved state. {state_str}", 2755)
         tool = admin_tool.certify_bot()
    
    # Uncertify
    elif data.op == enums.BotAdminOp.uncertify:
        if state != enums.BotState.certified:
            return api_error("Bot is not already certified", 2756)
        tool = admin_tool.uncertify_bot(data.reason)
    
    # Approve
    elif data.op == enums.BotAdminOp.approve:
        if state != enums.BotState.under_review:
            return api_error(f"You must claim this bot using +claim on the testing server. {state_str}", 2757)
        success_msg = f"Bot Approved Successfully! Invite it to the main server with https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot&guild_id={guild.id}&disable_guild_select=true&permissions=0"
        tool = admin_tool.approve_bot(data.reason)
    
    # Deny
    elif data.op == enums.BotAdminOp.deny:
        if state != enums.BotState.under_review:
            return api_error(f"You must claim this bot using +claim on the testing server. {state_str}", 2757)
        tool = admin_tool.deny_bot(data.reason)
    
    # Unverify
    elif data.op == enums.BotAdminOp.unverify:
        if state not in (enums.BotState.approved, enums.BotState.certified):
            return api_error(f"Bot is not in a approved state. {state_str}", 2755)
        tool = admin_tool.unverify_bot(data.reason)
      
    # Requeue
    elif data.op == enums.BotAdminOp.requeue:
        if state != enums.BotState.denied:
            return api_error(f"This bot has not been denied {state_str}", 2748)
        tool = admin_tool.requeue_bot(data.reason)
    
    # Transfer
    elif data.op == enums.BotAdminOp.transfer:
        try:
            new_owner = await get_user(int(data.ctx))
        except:
            new_owner = None
        if new_owner is None:
            return api_error("Invalid new owner for bot transfer specified", 2759)
        success_msg = "Bot has been transferred successfully!"
        tool = admin_tool.transfer_bot(data.reason, int(data.ctx))

    # Root update
    elif data.op == enums.BotAdminOp.root_update:
        try:
            new_state = enums.BotState(int(data.ctx))
        except:
            return api_error("Invalid state for root state update!", 2761)
        tool = admin_tool.root_update(data.reason, state, new_state)

    # Reset votes
    elif data.op == enums.BotAdminOp.reset_votes:
        task = True
        success_code = 202
        tool = admin_tool.reset_votes(data.reason)

    # Staff lock
    elif data.op == enums.BotAdminOp.staff_lock:
        if playground:
            return api_error("Staff bot locks are disabled in playground instances", 2765)
        req = await redis_db.get("fl_staff_req")
        req = orjson.loads(req) if req else []
        op = "lock"
        req.append({"op": "lock", "staff": data.mod, "bot_id": bot_id})
        await redis_db.set("fl_staff_req", orjson.dumps(req))
   
    # Staff unlock
    elif data.op == enums.BotAdminOp.staff_unlock:
        if playground:
            return api_error("Staff bot unlocks are disabled in playground instances", 2765)
        req = await redis_db.get("fl_staff_req")
        req = orjson.loads(req) if req else []
        req.append({"op": "unlock", "staff": data.mod, "bot_id": bot_id})
        await redis_db.set("fl_staff_req", orjson.dumps(req))

    # Bot lock
    elif data.op == enums.BotAdminOp.bot_lock:
        if not is_bot_admin(bot_id, data.mod):
            return api_error("You cannot lock or unlock a bot you do not own. If you are staff, ensure you have staff unlocked the bot using +sunlock <bot>", 2771, status_code = 403)
        sm = staff[2]
        try:
            lock = enums.BotLock(int(data.ctx))
        except:
            return api_error("Invalid lock state for bot!", 2766)
        if lock == enums.BotLock.locked:
            return api_error("You can't unlock a bot using bot_lock!", 2767)
        if sm.perm < 4 and lock not in enums.BotLock.locked:
            return api_error("Only staff with permlevel 4 and higher can use this lock type", 2768, status_code = 403)
        curr_lock = await db.fetchval("SELECT lock from bots WHERE bot_id = $1", bot_id)
        if curr_lock != enums.BotLock.unlocked:
            if curr_lock == enums.BotLock.locked:
                return api_error("This bot is already locked", 2769)
            elif sm.perm < 4:
                return api_error(f"This bot has been locked by staff and has a code of {curr_lock} ({enums.BotLock(curr_lock).__doc__}). Please ask a staff to unlock it", 2770, status_code = 403)
        tool = admin_tool.lock_bot(lock)

    # Bot unlock
    elif data.op == enums.BotAdminOp.bot_unlock:
        if not is_bot_admin(bot_id, data.mod):
            return api_error("You cannot lock or unlock a bot you do not own. If you are staff, ensure you have staff unlocked the bot using +sunlock <bot>", 2771, status_code = 403)
        sm = staff[2]
        curr_lock = await db.fetchval("SELECT lock from bots WHERE bot_id = $1", bot_id)
        if curr_lock != enums.BotLock.locked:
            if curr_lock == enums.BotLock.unlocked:
                return api_error("This bot is already locked", 2769)
            elif sm.perm < 4:
                return api_error(f"This bot has been locked by staff and has a code of {curr_lock} ({enums.BotLock(curr_lock).__doc__}). Please ask a staff to unlock it", 2770, status_code = 403)
        tool = admin_tool.unlock_bot()

    # Run the tool and return any errors it is capable of giving at this moment 
    if tool: 
        if not task:
            rc = await tool
            if rc is not None:
                return api_error(rc, 2760)
        else:
            asyncio.create_task(tool)
            
    return api_success(success_msg, 1000 if not success_msg else 1001, status_code = success_code)

@router.get("/queue/bots", response_model = BotQueueGet)
async def botlist_get_queue_api(request: Request):
    """Admin API to get the bot queue"""
    bots = await db.fetch("SELECT bot_id, prefix, description FROM bots WHERE state = $1 ORDER BY created_at ASC", enums.BotState.pending)
    return {"bots": [{"user": await get_bot(bot["bot_id"]), "prefix": bot["prefix"], "invite": await invite_bot(bot["bot_id"], api = True), "description": bot["description"]} for bot in bots]}

@router.get("/is_staff")
async def check_staff_member(request: Request, user_id: int, min_perm: int):
    """Admin route to check if a user is staff or not"""
    try:
        staff = is_staff(staff_roles, client.get_guild(main_server).get_member(user_id).roles, min_perm)
    except:
        return {"staff": False, "perm": 1, "sm": {}}
    return {"staff": staff[0], "perm": staff[1], "sm": staff[2].dict()}

