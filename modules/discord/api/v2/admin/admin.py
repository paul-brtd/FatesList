from modules.core import *
from .models import BotStateUpdate, APIResponse, BotTransfer, BotQueueGet, BotLock, BotListPartner, BotListPartnerAd, BotListPartnerChannel, IDResponse, enums, BotAdminOpEndpoint
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

@router.get("/partners")
async def get_partners(request: Request, f_ad: Optional[str] = None, f_site_ad: Optional[str] = None, f_server_ad: Optional[str] = None, id: Optional[uuid.UUID] = None, mod: Optional[int] = None, f_condition: Optional[str] = "AND"):
    """API to get partnerships:

    For clarification:

        - target: The ID of the bot or guild in question for the partnership

    Filters:

        f_site_ad is a site ad filter
        f_server_ad is a server ad filter
        f_ad is a both site ad and server ad filter
        mod is a mod filter. Useful in investigations
        id is a id filter

        Using multiple checks uses the f_condition value which can only be AND, AND NOT or OR
    """
    if f_condition not in ("AND", "OR", "AND NOT"):
        return abort(400)
    condition, args, i = [], [], 1
    if f_ad:
        condition.append(f"(site_ad ilike ${i} or server_ad ilike ${i})")
        args.append(f'%{f_ad}%')
        i+=1
    if f_site_ad:
        condition.append(f"site_ad ilike ${i}")
        args.append(f'%{f_site_ad}%')
        i+=1
    if f_server_ad:
        condition.append(f"server_ad ilike ${i}")
        args.append(f'%{f_server_ad}%')
        i+=1
    if id:
        condition.append(f"id = ${i}")
        args.append(id)
        i+=1
    if mod:
        condition.append(f"mod = ${i}")
        args.append(mod)
        i+=1
    if condition:
        cstr = "WHERE " + (" " + f_condition + " ").join(condition)
    else:
        cstr = ""
    partner_db = await db.fetch(f"SELECT id, mod, partner, publish_channel, edit_channel, type, invite, user_count, target, site_ad, server_ad FROM bot_list_partners {cstr}", *args)
    partners = []
    for partner in partner_db:
        mod = await get_user(partner["mod"])
        partner = await get_user(partner["partner"])
        try:
            site_ad = cleaner.clean_html(emd(markdown.markdown(partner["site_ad"], extensions = md_extensions)))
        except:
            site_ad = bleach.clean(emd(markdown.markdown(partner["site_ad"], extensions = md_extensions)))
        partners.append(dict(partner) | {"partner": {"user": partner}, "mod": {"user": mod}, "site_ad": site_ad})
    return {"partners": partners}

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
        await db.execute("INSERT INTO bot_list_partners (id, mod, partner, edit_channel, invite, user_count, target, type) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)", id, int(partner.mod), int(partner.partner), int(partner.edit_channel), invite.code, invite.approximate_member_count if partner.type == enums.PartnerType.guild else bot_user_count, partner.id if partner.type == enums.PartnerType.bot else invite.guild.id, partner.type)
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
    partner_check = await db.fetchval("SELECT COUNT(1) FROM bot_list_partners WHERE id = $1", partner.pid)
    if partner_check == 0:
        return ORJSONResponse({"done": False, "reason": "Partnership ID is invalid or partnership does not exist. Recheck the ID", "code": 4642}, status_code = 400)
    await db.execute(f"UPDATE bot_list_partners SET {ad_type.get_col()} = $1 WHERE id = $2", partner.ad, partner.pid)
    return {"done": True, "reason": None, "code": 1000, "id": id}

@router.patch("/partners/publish_channel", response_model = APIResponse)
async def set_partner_publish_channel(request: Request, partner: BotListPartnerChannel, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(partner.mod)
    if user is None or not is_staff(staff_roles, user.roles, 5)[0]:
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. The moderator in question does not have permission to perform this action!", "code": 9867}, status_code = 400)
    partner_check = await db.fetchval("SELECT COUNT(1) FROM bot_list_partners WHERE id = $1", partner.pid)
    if partner_check == 0:
        return ORJSONResponse({"done": False, "reason": "Partnership ID is invalid or partnership does not exist. Recheck the ID", "code": 4642}, status_code = 400)
    await db.execute("UPDATE bot_list_partners SET publish_channel = $1 WHERE id = $2", partner.publish_channel, partner.pid)
    return {"done": True, "reason": None, "code": 1000, "id": id}

@router.patch("/bots/{bot_id}/ops", response_model = APIResponse)
async def bot_admin_operation(request: Request, bot_id: int, data: BotAdminOpEndpoint, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    """Performs a bot admin operation. This is internal and only meant for our test server manager bot. 0 is the recursion bot for botlist-wide actions like vote resets every month"""
    if not secure_strcmp(Authorization, test_server_manager_key) and not secure_strcmp(Authorization, root_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(data.mod)
    
    if isinstance(data.op.__perm__, tuple):
        if data.op.__recursive__:
            perm = data.op.__perm__[0] if bot_id != 0 else data.op.__perm__[1]
    else:
        perm = data.op.__perm__
    staff = is_staff(staff_roles, user.roles, perm)
    if user is None or not staff[0]:
        return api_error(f"You do not have permission to perform this action! You need permlevel {perm}", 2764, status_code = 403)
    
    if data.op.__cooldown__:
        bucket_time = enums.cooldown_buckets[data.op.__cooldown__]
        coolkey = await redis_db.ttl(f"cooldown-{data.op.__cooldown__}-{data.mod}")
        if coolkey not in (-1, -2): # https://redis.io/commands/ttl, -2 means no key found and -1 means key exists but has no associated expire
            return api_error(f"This operation is on cooldown for {coolkey} seconds", 2767, status_code = 429)
        await redis_db.set(f"cooldown-{data.op.__cooldown__}-{data.mod}", 0, ex = int(bucket_time))

    if data.op.__reason_needed__ and not data.reason:
        return api_error("Please specify a reason for doing this!", 2753)
    
    admin_tool = BotListAdmin(bot_id, data.mod)
    
    if bot_id == 0 and not data.op.__recursive__:
        return api_error("This operation is not recursive. You must provide a nonzero bot id", 2763)
    elif bot_id == 0 and data.op.__recursive__:
        pass
    else:
        state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1", bot_id)
        owners = await db.fetchval("SELECT COUNT(1) FROM bot_owner WHERE bot_id = $1", bot_id)
        if state is None:
            return api_error("This bot does not exist", 2747, status_code = 404)
        try:
            state = enums.BotState(state)
        except:
            return api_error("Bot is in invalid state. Contact the developers of this list and ask them to fix this!", 2761)

        state_str = f"(state: {state.__doc__})"
    
    success_msg = None
    task = False
    success_code = 200
    tool = None

    if data.op == enums.BotAdminOp.requeue:
        if state != enums.BotState.denied:
            return api_error(f"This bot has not been denied {state_str}", 2748)
        tool = admin_tool.requeue_bot(data.reason)

    elif data.op == enums.BotAdminOp.unban:
        if state != enums.BotState.banned:
            return api_error(f"This bot has not been banned {state_str}", 2749)
        tool = admin_tool.unban_bot(data.reason)
        
    elif data.op == enums.BotAdminOp.unclaim:
        if state != enums.BotState.under_review:
            return api_error(f"This bot is not currently claimed and hence cannot be unclaimed {state_str}", 2749)
        tool = admin_tool.unclaim_bot()

    elif data.op == enums.BotAdminOp.claim:
        if state == enums.BotState.under_review:
            verifier = await db.fetchval("SELECT verifier FROM bots WHERE bot_id = $1", bot_id)
            return api_error(f"This bot has already been claimed by <@{verifier}> ({verifier})", 2750)

        elif state != enums.BotState.pending:
            return api_error(f"This bot is not currently pending review {state_str}", 2751)
        tool = admin_tool.claim_bot()

    elif data.op == enums.BotAdminOp.ban:
        if state == enums.BotState.banned:
            return api_error("This bot has already been banned", 2752)
        tool = admin_tool.ban_bot(data.reason)

    elif data.op == enums.BotAdminOp.certify:
         if state == enums.BotState.certified:
             return api_error("Bot is already certified", 2754)
         elif state != enums.BotState.approved:
             return api_error(f"Bot is not in a approved state. {state_str}", 2755)
         tool = admin_tool.certify_bot()

    elif data.op == enums.BotAdminOp.uncertify:
        if state != enums.BotState.certified:
            return api_error("Bot is not already certified", 2756)
        tool = admin_tool.uncertify_bot(data.reason)

    elif data.op == enums.BotAdminOp.approve:
        if state != enums.BotState.under_review:
            return api_error(f"You must claim this bot using +claim on the testing server. {state_str}", 2757)
        success_msg = f"Bot Approved Successfully! Invite it to the main server with https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot&guild_id={guild.id}&disable_guild_select=true&permissions=0"
        tool = admin_tool.approve_bot(data.reason)

    elif data.op == enums.BotAdminOp.deny:
        if state != enums.BotState.under_review:
            return api_error(f"You must claim this bot using +claim on the testing server. {state_str}", 2757)
        tool = admin_tool.deny_bot(data.reason)
    
    elif data.op == enums.BotAdminOp.unverify:
        if state not in (enums.BotState.approved, enums.BotState.certified):
            return api_error(f"Bot is not in a approved state. {state_str}", 2755)
        tool = admin_tool.unverify_bot(data.reason)

    elif data.op == enums.BotAdminOp.transfer:
        try:
            new_owner = await get_user(int(data.ctx))
        except:
            new_owner = None
        if new_owner is None:
            return api_error("Invalid new owner for bot transfer specified", 2759)
        success_msg = "Bot has been transferred successfully!"
        tool = admin_tool.transfer_bot(data.reason, int(data.ctx))

    elif data.op == enums.BotAdminOp.root_update:
        try:
            new_state = enums.BotState(int(data.ctx))
        except:
            return api_error("Invalid state for root state update!", 2761)
        tool = admin_tool.root_update(data.reason, state, new_state)

    elif data.op == enums.BotAdminOp.reset_votes:
        task = True
        success_code = 202
        tool = admin_tool.reset_votes(data.reason)

    elif data.op == enums.BotAdminOp.staff_lock:
        if playground:
            return api_error("Staff bot locks are disabled in playground instances", 2765)
        req = await redis_db.get("fl_staff_req")
        req = orjson.loads(req) if req else []
        op = "lock"
        req.append({"op": "lock", "staff": data.mod, "bot_id": bot_id})
        await redis_db.set("fl_staff_req", orjson.dumps(req))
    
    elif data.op == enums.BotAdminOp.staff_unlock:
        if playground:
            return api_error("Staff bot unlocks are disabled in playground instances", 2765)
        req = await redis_db.get("fl_staff_req")
        req = orjson.loads(req) if req else []
        req.append({"op": "unlock", "staff": data.mod, "bot_id": bot_id})
        await redis_db.set("fl_staff_req", orjson.dumps(req))

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

