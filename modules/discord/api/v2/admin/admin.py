from modules.core import *
from .models import BotStateUpdate
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
