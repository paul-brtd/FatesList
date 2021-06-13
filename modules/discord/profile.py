from ..core import *
from ..badges import *

router = APIRouter(
    prefix = "/profile",
    tags = ["Profile"],
    include_in_schema = False
)

@router.get("/me")
async def redirect_me(request: Request, preview: bool = False):
    if "user_id" not in request.session.keys():
        return RedirectResponse("/")
    return await get_user_profile(request, int(request.session.get("user_id")), preview = preview)

@router.get("/{user_id}")
async def profile_of_user_generic(request: Request, user_id: int, preview: bool = False):
    return await get_user_profile(request, user_id, preview = preview)

async def get_user_profile(request, user_id: int, preview: bool):
    guild = client.get_guild(main_server)
    if guild is None:
        return await templates.e(request, "Site is still loading...")
    if request.session.get("user_id"):
        dpy_viewer = guild.get_member(int(request.session.get("user_id")))
    else:
        dpy_viewer = None
    dpy_member = guild.get_member(user_id)
    if dpy_viewer is None:
        admin = False
    else:
        admin = is_staff(staff_roles, dpy_viewer.roles, 4)[0]
    if admin or (request.session.get("user_id") and user_id == int(request.session.get("user_id"))):
        personal = True
    else:
        personal = False
    return await _profile_of_user(request, user_id, personal = personal if personal and not preview else False, admin = admin, dpy_member = dpy_member)

async def _profile_of_user(request: Request, user_id: int, personal: bool, admin: bool, dpy_member: Optional[discord.Member]):
    state = await db.fetchval("SELECT state FROM users WHERE user_id = $1", user_id)
    if (not admin and state == enums.UserState.global_ban) or state == enums.UserState.ddr_ban:
        return abort(404)
    user = await get_user(int(user_id))
    if not user:
        return await templates.e(request, "Profile Not Found", 404)
    bots = await db.fetch("SELECT DISTINCT bots.bot_id, bots.state FROM bot_owner INNER JOIN bots ON bot_owner.bot_id = bots.bot_id WHERE bot_owner.owner = $1", user_id)
    bot_id_lst = [obj["bot_id"] for obj in bots]
    fetchq = []
    for bot_id in bot_id_lst:
        base_query = ("SELECT description, banner, state, votes, servers, bot_id, invite FROM bots ")
        if not personal:
            query = base_query + "WHERE bot_id = $1 and (state = 0 OR state = 6) ORDER BY votes"
        else:
            query = base_query + "WHERE bot_id = $1 ORDER BY votes"
        data = await db.fetchrow(query, bot_id)
        fetchq.append(data)
    user_bots = await parse_index_query(fetchq)
    if personal:
        user_info = await db.fetchrow("SELECT user_id, js_allowed, api_token, badges, description, coins FROM users WHERE user_id = $1", user_id)
    else:
        user_info = await db.fetchrow("SELECT user_id, badges, description, coins FROM users WHERE user_id = $1", user_id)
    if user_info is None:
        return abort(404)
    guild = client.get_guild(main_server)
    return await templates.TemplateResponse("profile.html", {"request": request, "username": request.session.get("username", False), "user_bots": user_bots, "user": user, "avatar": request.session.get("avatar"), "user_id": user_id, "personal": personal, "badges": get_badges(dpy_member, user_info["badges"], bots), "user_info": user_info, "coins": user_info["coins"]})

