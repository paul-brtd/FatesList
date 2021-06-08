from modules.core import *
from .models import APIResponse, BotListPartner, BotListPartnerAd, BotListPartnerChannel, IDResponse, enums
from ..base import API_VERSION
import uuid
import bleach
from lxml.html.clean import Cleaner

cleaner = Cleaner()

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/admin",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Admin (Partnerships)"]
)

class InvalidInvite(Exception):
    pass

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
