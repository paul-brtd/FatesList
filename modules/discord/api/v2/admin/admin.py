from modules.core import *
from .models import BotStateUpdate, APIResponse, BotTransfer, BotQueueGet, BotLock, BotListPartner, BotListPartnerAd, BotListPartnerChannel, IDResponse, enums, BotQueueAdminPatch
from modules.discord.admin import admin_dashboard
from ..base import API_VERSION
import uuid

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

@router.patch("/bots/{bot_id}/state/root")
async def bot_root_update_api(request: Request, bot_id: int, data: BotStateUpdate, Authorization: str = Header("ROOT_KEY")):
    """Root API to update a bots state. Needs the root key"""
    if not secure_strcmp(Authorization, root_key):
        return abort(401)
    await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", data.state, bot_id)
    return {"done": True, "reason": None, "code": 1000}

@router.patch("/bots/{bot_id}/lock")
async def bot_lock_unlock_api(request: Request, bot_id: int, data: BotLock, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    """Locks or unlocks a bot for staff to edit. This is internal and only meant for our test server manager bot"""
    if playground:
        return ORJSONResponse({"done": False, "reason": "Bot locks are disabled in playground instances", "code": 9867}, status_code = 400)
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(data.mod)
    if user is None or not is_staff(staff_roles, user.roles, 4)[0]: 
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. The moderator in question does not have permission to perform this action!", "code": 9867}, status_code = 400)
    req = await redis_db.get("fl_staff_req")
    req = orjson.loads(req) if req else []
    op = "lock" if data.lock else "unlock"
    req.append({"op": op, "staff": data.mod, "bot_id": bot_id})
    await redis_db.set("fl_staff_req", orjson.dumps(req))
    return {"done": True, "reason": None, "code": 1000, "op": op}

@router.get("/err")
@router.post("/err", response_model = APIResponse)
async def error_maker(request: Request):
    error = int("haha")

@router.post("/partners", response_model = IDResponse)
async def new_partner(request: Request, partner: BotListPartner, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(int(partner.mod))
    if user is None or not is_staff(staff_roles, user.roles, 5)[0]:
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. The moderator in question does not have permission to perform this action!", "code": 9867}, status_code = 400)
    prev_partner = await db.fetchval("SELECT COUNT(1) FROM bot_list_partners WHERE partner = $1", int(partner.partner))
    if prev_partner > 2:
        return ORJSONResponse({"done": False, "reason": "This user already has two partnerships"}, status_code = 400)
    channel = client.get_channel(int(partner.edit_channel))
    if not channel:
        return ORJSONResponse({"done": False, "reason": "Partnership edit channel does not exist"}, status_code = 400)
    try:
        invite = await client.fetch_invite(partner.invite, with_expiration = True)
        if not invite.guild:
            raise InvalidInvite("Invite not for server")
        if not invite.unlimited:
            raise InvalidInvite(f"Invite is not unlimited use. Max age is {invite.max_age} and unlimited is {invite.unlimited}.")
    except Exception as exc:
        return ORJSONResponse({"done": False, "reason": f"Could not resolve invite as {type(exc).__name__}: {exc}. Double check the invite"}, status_code = 400)
    id = uuid.uuid4()
    if partner.type == enums.PartnerType.bot:
        if not partner.id:
            return ORJSONResponse({"done": False, "reason": f"Bot not passed to API. Contact the developers of this app", "code": 5682}, status_code = 400)
        bot_user_count = await db.fetchval("SELECT user_count FROM bots WHERE bot_id = $1", int(partner.id))
        if not bot_user_count:
            return ORJSONResponse({"done": False, "reason": f"Bot has not yet posted user count yet or is not on Fates List", "code": 4748}, status_code = 400)
    try:
        await db.execute("INSERT INTO bot_list_partners (pid, mod, partner, edit_channel, invite, user_count, id, type) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)", id, int(partner.mod), int(partner.partner), int(partner.edit_channel), invite.code, invite.approximate_member_count if partner.type == enums.PartnerType.guild else bot_user_count, partner.id if partner.type == enums.PartnerType.bot else invite.guild.id, partner.type)
    except Exception as exc:
        return ORJSONResponse({"done": False, "reason": f"Could not create partnership as {type(exc).__name__}: {exc}. Contact Rootspring for help with this error"}, status_code = 400)
    embed = discord.Embed(title="Partnership Channel Recorded", description=f"Put your advertisement here, then ask a moderator to run +partner ad {id} <message link of ad>")
    await channel.send(embed = embed)
    return {"done": True, "reason": None, "code": 1000, "id": id}

@router.patch("/partners/ad/{ad_type}", response_model = APIResponse)
async def set_partner_ad(request: Request, ad_type: enums.PartnerAdType, partner: BotListPartnerAd, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(partner.mod)
    if user is None or not is_staff(staff_roles, user.roles, 5)[0]:
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. The moderator in question does not have permission to perform this action!", "code": 9867}, status_code = 400)
    partner_check = await db.fetchval("SELECT COUNT(1) FROM bot_list_partners WHERE pid = $1", partner.pid)
    if partner_check == 0:
        return ORJSONResponse({"done": False, "reason": "Partnership ID is invalid or partnership does not exist. Recheck the ID", "code": 4642}, status_code = 400)
    await db.execute(f"UPDATE bot_list_partners SET {ad_type.get_col()} = $1 WHERE pid = $2", partner.ad, partner.pid)
    return {"done": True, "reason": None, "code": 1000, "id": id}

@router.patch("/partners/publish_channel", response_model = APIResponse)
async def set_partner_publish_channel(request: Request, partner: BotListPartnerChannel, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(partner.mod)
    if user is None or not is_staff(staff_roles, user.roles, 5)[0]:
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. The moderator in question does not have permission to perform this action!", "code": 9867}, status_code = 400)
    partner_check = await db.fetchval("SELECT COUNT(1) FROM bot_list_partners WHERE pid = $1", partner.pid)
    if partner_check == 0:
        return ORJSONResponse({"done": False, "reason": "Partnership ID is invalid or partnership does not exist. Recheck the ID", "code": 4642}, status_code = 400)
    await db.execute("UPDATE bot_list_partners SET publish_channel = $1 WHERE pid = $2", partner.publish_channel, partner.pid)
    return {"done": True, "reason": None, "code": 1000, "id": id}

@router.patch("/bots/{bot_id}/queue/op", response_model = APIResponse)
async def bot_queue_operation(request: Request, bot_id: int, data: BotQueueAdminPatch, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    """Performs a bot queue operation. This is internal and only meant for our test server manager bot"""
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(data.mod)
    if user is None or not is_staff(staff_roles, user.roles, data.op.__perm__)[0]:
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. The moderator in question does not have permission to perform this action!", "code": 9867}, status_code = 400)
    admin_tool = BotListAdmin(bot_id, data.mod)
    state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)
    if state is None:
        return ORJSONResponse({"done": False, "reason": "This bot does not exist", "code": 2747}, status_code = 404)
    state_str = f"(state: {enums.BotState(state).__doc__})"
    success_msg = None

    if data.op == enums.AdminQueueOp.requeue:
        if state != enums.BotState.denied:
            return ORJSONResponse({"done": False, "reason": "This bot has not been denied {state_str}", "code": 2747}, status_code = 404)
        tool = admin_tool.requeue_bot()

    elif data.op == enums.AdminQueueOp.unban:
        if state != enums.BotState.unban:
            return ORJSONResponse({"done": False, "reason": "This bot has not been banned {state_str}", "code": 2747}, status_code = 404)
        tool = admin_tool.unban_bot()
        
    elif data.op == enums.AdminQueueOp.unclaim:
        if state != enums.BotState.under_review:
            return ORJSONResponse({"done": False, "reason": f"This bot is not currently claimed and hence cannot be unclaimed {state_str}", "code": 2746}, status_code = 400)
        tool = admin_tool.unclaim_bot()

    elif data.op == enums.AdminQueueOp.claim:
        if state == enums.BotState.under_review:
            verifier = await db.fetchval("SELECT verifier FROM bots WHERE bot_id = $1", bot_id)
            return ORJSONResponse({"done": False, "reason": f"This bot has already been claimed by <@{verifier}> ({verifier})", "code": 2647}, status_code = 400)

        elif state != enums.BotState.pending:
            return ORJSONResponse({"done": False, "reason": f"This bot is not currently pending review {state_str}", "code": 5747}, status_code = 400)
        tool = admin_tool.claim_bot()

    elif data.op == enums.AdminQueueOp.ban:
        if state == enums.BotState.banned:                                                                   
            return ORJSONResponse({"done": False, "reason": "This bot has already been banned", "code": 2748}, status_code = 400)
        elif not data.reason:
            return ORJSONResponse({"done": False, "reason": "Please specify a reason before banning", "code": 2751}, status_code = 400)
        tool = admin_tool.ban_bot(data.reason)

    elif data.op == enums.AdminQueueOp.certify:
         if state == enums.BotState.certified: 
             return ORJSONResponse({"done": False, "reason": "Bot is already certified", "code": 8826}, status_code = 400) 
         elif state !=enums.BotState.approved:
             return ORJSONResponse({"done": False, "reason": f"Bot is not in a approved state. State is {enums.BotState(state).__doc__}.", "code": 8126}, status_code = 400)
         tool = admin_tool.certify_bot()

    elif data.op == enums.AdminQueueOp.uncertify:
        if state != enums.BotState.certified:
            return ORJSONResponse({"done": False, "reason": "Bot is not already certified", "code": 8826}, status_code = 400)
        tool = admin_tool.uncertify_bot()

    elif data.op == enums.AdminQueueOp.approve:
        if state != enums.BotState.under_review:
            return ORJSONResponse({"done": False, "reason": f"You must claim this bot using +claim on the testing server. {state_str}"}, status_code = 400)
        if not data.reason:
            data.reason = approve_feedback
        if len(data.reason) < 7:
            return ORJSONResponse({"done": False, "reason": "Feedback must either not be provided or must be larger than 7 characters!", "code": 3836}, status_code = 400)
        success_msg = f"Bot Approved Successfully! Invite it to the main server with https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot&guild_id={guild.id}&disable_guild_select=true&permissions=0"
        tool = admin_tool.approve_bot(data.reason)

    elif data.op == enums.AdminQueueOp.deny:
        if state != enums.BotState.under_review:
            return ORJSONResponse({"done": False, "reason": f"You must claim this bot using +claim on the testing server. {state_str}"}, status_code = 400)
        if not data.reason:
            data.reason = deny_feedback
        if len(data.reason) < 7:
            return ORJSONResponse({"done": False, "reason": "Feedback must either not be provided or must be larger than 7 characters!", "code": 3836}, status_code = 400)
        tool = admin_tool.deny_bot(data.reason)
    
    elif data.op == enums.AdminQueueOp.unverify:
        if state not in (enums.BotState.approved, enums.BotState.certified):
            return ORJSONResponse({"done": False, "reason": f"This bot is not verified {state_str}!"}, status_code = 400)
        if not data.reason:
            return ORJSONResponse({"done": False, "reason": "Please specify a reason before unverifying", "code": 2751}, status_code = 400)
        tool = admin_tool.unverify_bot(data.reason)

    rc = await tool
    if rc is not None:
        return ORJSONResponse({"done": False, "reason": rc, "code": 4646}, status_code = 400)
    return {"done": True, "reason": success_msg, "code": 1000}

@router.patch("/bots/{bot_id}/main_owner", response_model = APIResponse)
async def transfer_bot_api(request: Request, bot_id: int, data: BotTransfer, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    guild = client.get_guild(main_server)
    try:
        user = guild.get_member(data.mod)
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
    admin_tool = BotListAdmin(bot_id, data.mod)
    rc = await admin_tool.transfer_bot(int(data.new_owner))
    if rc is None:
        return {"done": True, "reason": "Bot Transferred Successfully!", "code": 1001}
    return ORJSONResponse({"done": False, "reason": rc, "code": 3869}, status_code = 400)

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

