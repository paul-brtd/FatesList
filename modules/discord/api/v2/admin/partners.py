import uuid

import bleach
from lxml.html.clean import Cleaner

from modules.core import *

from ..base import API_VERSION
from .models import (APIResponse, BotListAdminRoute, BotListPartner,
                     BotListPartnerAd, BotListPartnerChannel,
                     BotListPartnerPublish, IDResponse, enums)

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
    partner_db = await db.fetch(f"SELECT id, mod, partner, publish_channel, edit_channel, type, invite, user_count, target, site_ad, server_ad, created_at, published FROM bot_list_partners {cstr}", *args)
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

async def _invite_resolver(code):
    try:
        invite = await client.fetch_invite(code, with_expiration = True)
        if not invite.guild:
            raise InvalidInvite("Invite not for server")
        if not invite.unlimited:
            raise InvalidInvite(
                f"Invite is not unlimited use. Max age is {invite.max_age} and unlimited is {invite.unlimited}."
            )
    except Exception as exc:
        return False, api_error(
            f"Could not resolve invite as {type(exc).__name__}: {exc}. Double check the invite **and** the API code itself"
        )
    return True, invite

@router.post("/partners", response_model = IDResponse)
async def new_partner(request: Request, partner: BotListPartner, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, manager_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(int(partner.mod))
    if user is None or not is_staff(staff_roles, user.roles, 5)[0]:
        return api_no_perm(5)

    prev_partner = await db.fetchval("SELECT COUNT(1) FROM bot_list_partners WHERE partner = $1", int(partner.partner))
    if prev_partner > 2:
        return api_error(
            "This user already has two or more partnerships"
        )

    channel = guild.get_channel(int(partner.edit_channel))
    if not channel:
        return api_error(
            "Partnership edit channel does not exist"
        )
    
    invite = await _invite_resolver(partner.invite)
    if not invite[0]:
        return invite[1]
    invite = invite[1]

    id = uuid.uuid4()
    if partner.type == enums.PartnerType.bot:
        if not partner.id:
            return api_error(
                f"Bot not passed to API. Contact the developers of this app"
            )
        
        bot_user_count = await db.fetchval("SELECT user_count FROM bots WHERE bot_id = $1", int(partner.id))
        if not bot_user_count:
            return api_error(
                f"Bot has not yet posted user count yet or is not on Fates List"
            )
    
    try:
        await db.execute("INSERT INTO bot_list_partners (id, mod, partner, edit_channel, invite, user_count, target, type) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)", id, int(partner.mod), int(partner.partner), int(partner.edit_channel), invite.code, invite.approximate_member_count if partner.type == enums.PartnerType.guild else bot_user_count, partner.id if partner.type == enums.PartnerType.bot else invite.guild.id, partner.type)
    except Exception as exc:
        return api_error(
            f"Could not create partnership as {type(exc).__name__}: {exc}. Contact Rootspring for help with this error"
        )
    embed = discord.Embed(
        title="Partnership Channel Recorded", 
        description=f"Put your advertisement here, then ask a moderator to run +partner ad {id} <message link of ad>"
    )
    await channel.send(embed = embed)
    return api_success(id = id)

@router.patch("/partners/{pid}/ad/{ad_type}", response_model = APIResponse)
async def set_partner_ad(request: Request, pid: uuid.UUID, ad_type: enums.PartnerAdType, partner: BotListPartnerAd, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, manager_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(partner.mod)
    if user is None or not is_staff(staff_roles, user.roles, 5)[0]:
        return api_no_perm()
    
    if len(partner.ad) > 1960 and ad_type == enums.PartnerAdType.server:
        return api_error(
            "Partnership server ad can only be a maximum of 1960 characters long."
        )

    partner_check = await db.fetchval("SELECT COUNT(1) FROM bot_list_partners WHERE id = $1", pid)
    if partner_check == 0:
        return api_error(
            "Partnership ID is invalid or partnership does not exist. Recheck the ID"
        )
    await db.execute(f"UPDATE bot_list_partners SET {ad_type.get_col()} = $1 WHERE id = $2", partner.ad, pid)
    return api_success()

@router.delete("/partners/{pid}", response_model = APIResponse)
async def delete_partnership(request: Request, pid: uuid.UUID, partner: BotListAdminRoute, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, manager_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(partner.mod)
    if user is None or not is_staff(staff_roles, user.roles, 5)[0]:
        return api_no_perm(5)
    partner_check = await db.fetchval("SELECT COUNT(1) FROM bot_list_partners WHERE id = $1", pid)
    if partner_check == 0:
        return api_error(
            "Partnership ID is invalid or partnership does not exist. Recheck the ID"
        )
    await db.execute("DELETE FROM bot_list_partners WHERE id = $1", pid)
    return api_success()

@router.patch("/partners/{pid}/publish_channel", response_model = APIResponse)
async def set_partner_publish_channel(request: Request, pid: uuid.UUID, partner: BotListPartnerChannel, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, manager_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(partner.mod)
    if user is None or not is_staff(staff_roles, user.roles, 5)[0]:
        return api_no_perm(5)

    partner_check = await db.fetchval("SELECT COUNT(1) FROM bot_list_partners WHERE id = $1", pid)
    if partner_check == 0:
        return api_error(
            "Partnership ID is invalid or partnership does not exist. Recheck the ID"
        )
    await db.execute("UPDATE bot_list_partners SET publish_channel = $1 WHERE id = $2", partner.publish_channel, pid)
    return api_success()

@router.post("/partners/{pid}/publish", response_model = APIResponse)
async def publish_partnership(request: Request, pid: uuid.UUID, partner: BotListPartnerPublish, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    if not secure_strcmp(Authorization, manager_key):
        return abort(401)
    guild = client.get_guild(main_server)
    user = guild.get_member(partner.mod)
    if user is None or not is_staff(staff_roles, user.roles, 5)[0]:
        return api_no_perm()
    publish = await db.fetchrow("SELECT invite, publish_channel, type, target, server_ad FROM bot_list_partners WHERE id = $1", pid)
    if not publish:
        return api_error(
            "This partnership does not exist"
        )
    
    elif not publish["publish_channel"]:
        return api_error(
            "This partnership does not have a publish channel set yet"
        )
    
    invite = await _invite_resolver(publish["invite"])
    if not invite[0]:
        return invite[1]
    invite = invite[1]

    channel = guild.get_channel(publish["publish_channel"])
    if not channel:
        return api_error(
            "Set publish channel does not exist anymore"            
        )

    if publish["type"] == enums.PartnerType.bot:
        member = guild.get_member(publish["target"])
        if not member:
            return api_error(
                "Bot associated with partnership is not in this server anymore"        
            )
        embed = discord.Embed(
            title = member.name 
        )
        embed.add_field(name="Hi there!", value = publish["server_ad"])
        embed.add_field(name="Support Server", value = f"https://discord.gg/{invite.code}")
    elif publish["type"] == enums.PartnerAdType.server:
        embed = discord.Embed(
            title = invite.guild.name         
        )
        embed.add_field(name="Hi there!", value = publish["server_ad"])
    await db.execute("UPDATE bot_list_partners SET published = true WHERE id = $1", pid)
    if partner.embed:
        await channel.send(embed = embed)
    await channel.send(publish["server_ad"])
