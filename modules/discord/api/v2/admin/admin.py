from modules.core import *
from .models import BotStateUpdate, BotCertify, BotBan, APIResponse, BotUnderReview, BotTransfer, BotQueueGet, BotQueuePatch
from modules.discord.admin import admin_dashboard
from ..base import API_VERSION

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/admin",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Admin"]
)

@router.get("/console")
async def botlist_admin_console_api(request: Request):
    """API to get raw admin console info"""
    return await admin_dashboard(request) # Just directly render the admin dashboard. It knows what to do

@router.patch("/bots/{bot_id}/state")
async def bot_root_update_api(request: Request, bot_id: int, data: BotStateUpdate, Authorization: str = Header("ROOT_KEY")):
    """Root API to update a bots state. Needs the root key"""
    if not secure_strcmp(Authorization, root_key):
        return abort(401)
    await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", data.state, bot_id)
    return {"done": True, "reason": None, "code": 1000}

@router.patch("/bots/{bot_id}/under_review", response_model = APIResponse)
async def bot_under_review_api(request: Request, bot_id: int, data: BotUnderReview, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    """Put a bot in queue under review or back in queue. This is internal and only meant for our test server manager bot"""
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(int(data.mod))
    if user is None or not is_staff(staff_roles, user.roles, 2)[0] or (data.requeue == 1 and not is_staff(staff_roles, user.roles, 3)[0]):
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. The moderator in question does not have permission to perform this action!", "code": 9867}, status_code = 400)
    admin_tool = BotListAdmin(bot_id, data.mod)

    if data.requeue == 1 or data.requeue == 2:
        # Requeue or unclaim
        if data.requeue == 1:
            state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1 AND state = $2", bot_id, enums.BotState.denied)
            if state is None:
                return ORJSONResponse({"done": False, "reason": "This bot does not exist", "code": 2747}, status_code = 404)
            tool = admin_tool.unban_requeue_bot(state)
        
        elif data.requeue == 2:
            state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)
            if state is None:
                return ORJSONResponse({"done": False, "reason": "This bot does not exist", "code": 2747}, status_code = 404)   
            if state != enums.BotState.under_review:
                return ORJSONResponse({"done": False, "reason": f"This bot is not currently claimed and hence cannot be unclaimed (state: {enums.BotState(state).__doc__})", "code": 2746}, status_code = 400)
            tool = admin_tool.unclaim_bot()
        if state is None:
            return ORJSONResponse({"done": False, "reason": "This bot either does not exist or may already be claimed by someone else...", "code": 2747}, status_code = 404)
        rc = await tool
    else:
        state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id) 
        if state is None:
            return ORJSONResponse({"done": False, "reason": "This bot does not exist", "code": 2747}, status_code = 404)
        if state == enums.BotState.under_review:
            verifier = await db.fetchval("SELECT verifier FROM bots WHERE bot_id = $1", bot_id)
            return ORJSONResponse({"done": False, "reason": f"This bot has already been claimed by <@{verifier}> ({verifier})", "code": 2647}, status_code = 400)
        elif state != enums.BotState.pending:
            return ORJSONResponse({"done": False, "reason": f"This bot is not currently pending review (state is {enums.BotState(state).__doc__})", "code": 5747}, status_code = 400)

        rc = await admin_tool.claim_bot()
    if rc is not None:
        return ORJSONResponse({"done": False, "reason": rc, "code": 4646}, status_code = 400)
    return {"done": True, "reason": None, "code": 1000}

@router.patch("/bots/{bot_id}/ban", response_model = APIResponse)
async def ban_unban_bot_api(request: Request, bot_id: int, data: BotBan, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    guild = client.get_guild(main_server) 
    user = guild.get_member(int(data.mod)) 
    if user is None or not is_staff(staff_roles, user.roles, 3)[0]:
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. The moderator in question does not have permission to perform this action!", "code": 9867}, status_code = 400)
    admin_tool = BotListAdmin(bot_id, data.mod)
    state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)
    if state is None:
        return ORJSONResponse({"done": False, "reason": "This bot does not exist", "code": 2747}, status_code = 404)
    if data.ban:
        if state == enums.BotState.banned:
            return ORJSONResponse({"done": False, "reason": "This bot has already been banned", "code": 2748}, status_code = 400)
        elif not data.reason:
            return ORJSONResponse({"done": False, "reason": "Please specify a reason before banning", "code": 2751}, status_code = 400)
        await admin_tool.ban_bot(data.reason)
    else:
        if state == enums.BotState.banned:
            await admin_tool.unban_requeue_bot(state)
        else:
            return ORJSONResponse({"done": False, "reason": "This bot is not currently banned", "code": 2749}, status_code = 400)
    return {"done": True, "reason": None, "code": 1000}

@router.patch("/bots/{bot_id}/certify", response_model = APIResponse)
async def certify_bot_api(request: Request, bot_id: int, data: BotCertify, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    guild = client.get_guild(main_server)
    try:
        user = guild.get_member(int(data.mod))
    except ValueError:
        user = None
    if user is None or not is_staff(staff_roles, user.roles, 5)[0]:
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. The moderator in question does not have permission to perform this action!", "code": 8826}, status_code = 400)
    state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)
    admin_tool = BotListAdmin(bot_id, data.mod)
    if data.certify:
        if state == enums.BotState.certified:
            return ORJSONResponse({"done": False, "reason": "Bot is already certified", "code": 8826}, status_code = 400)
        elif state !=enums.BotState.approved:
            return ORJSONResponse({"done": False, "reason": f"Bot is not in a approved state. State is {enums.BotState(state).__doc__}.", "code": 8126}, status_code = 400)
        rc = await admin_tool.certify_bot()
    else:
        if state != enums.BotState.certified:
            return ORJSONResponse({"done": False, "reason": "Bot is not already certified", "code": 8826}, status_code = 400)
        rc = await admin_tool.uncertify_bot()

    if rc is None:
        return {"done": True, "reason": None, "code": 1000}
    return ORJSONResponse({"done": False, "reason": rc, "code": 3732}, status_code = 400)

@router.patch("/bots/{bot_id}/main_owner", response_model = APIResponse)
async def transfer_bot_api(request: Request, bot_id: int, data: BotTransfer, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    guild = client.get_guild(main_server)
    try:
        user = guild.get_member(int(data.mod))
    except ValueError:
        user = None
    if user is None or not is_staff(staff_roles, user.roles, 4)[0]:
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. The moderator in question does not have permission to perform this action!", "code": 8826}, status_code = 400)
    try:
        new_owner = await get_user(int(data.new_owner))
    except:
        new_owner = None
    if new_owner is None:
        return ORJSONResponse({"done": False, "reason": "Invalid new owner specified.", "code": 8827}, status_code = 400)
    admin_tool = BotListAdmin(bot_id, int(data.mod))
    rc = await admin_tool.transfer_bot(int(data.new_owner))
    if rc is None:
        return {"done": True, "reason": "Bot Transferred Successfully!", "code": 1001}
    return ORJSONResponse({"done": False, "reason": rc, "code": 3869}, status_code = 400)

@router.get("/queue/bots", response_model = BotQueueGet)
async def botlist_get_queue_api(request: Request):
    """Admin API to get the bot queue"""
    bots = await db.fetch("SELECT bot_id, prefix, description FROM bots WHERE state = $1 ORDER BY created_at ASC", enums.BotState.pending)
    return {"bots": [{"user": await get_bot(bot["bot_id"]), "prefix": bot["prefix"], "invite": await invite_bot(bot["bot_id"], api = True), "description": bot["description"]} for bot in bots]}

@router.patch("/bots/{bot_id}/queue", response_model = APIResponse)
async def botlist_edit_queue_api(request: Request, bot_id: int, data: BotQueuePatch, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    """Admin API to approve/verify or deny a bot on Fates List"""
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    
    try:
        admin_tool = BotListAdmin(bot_id, int(data.mod))
    except:
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. Please contact the developers of this bot!", "code": 3839}, status_code = 400)
 
    if not data.feedback:
        if data.approve:
            data.feedback = approve_feedback
        else:
            data.feedback = deny_feedback

    if len(data.feedback) < 3:
        return ORJSONResponse({"done": False, "reason": "Feedback must either not be provided or must be larger than 3 characters!", "code": 3836}, status_code = 400)
    guild = client.get_guild(main_server)
    try:
        user = guild.get_member(int(data.mod))
    except ValueError:
        user = None
    if user is None or not is_staff(staff_roles, user.roles, 2)[0]:
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. The moderator in question does not have permission to perform this action!", "code": 3867}, status_code = 400)

    if data.approve:
        rc = await admin_tool.approve_bot(data.feedback)
    else:
        rc = await admin_tool.deny_bot(data.feedback)
    
    if rc is None:
        if not data.approve:
            return {"done": True, "reason": "Bot Denied Successfully!", "code": 1001}
        return {"done": True, "reason": f"Bot Approved Successfully! Invite it to the main server with https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot&guild_id={guild.id}&disable_guild_select=true&permissions=0", "code": 1001}
    return ORJSONResponse({"done": False, "reason": rc, "code": 3869}, status_code = 400)

@router.get("/is_staff")
async def check_staff_member(request: Request, user_id: int, min_perm: int):
    """Admin route to check if a user is staff or not"""
    try:
        staff = is_staff(staff_roles, client.get_guild(main_server).get_member(user_id).roles, min_perm)
    except:
        return {"staff": False, "perm": 1, "sm": {}}
    return {"staff": staff[0], "perm": staff[1], "sm": staff[2].dict()}

