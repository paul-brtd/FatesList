from ..core import *
from ..badges import *

router = APIRouter(
    prefix = "/profile",
    tags = ["Profile"],
    include_in_schema = False
)

@router.get("/me")
async def redirect_me(request: Request):
    if "userid" not in request.session.keys():
        return RedirectResponse("/")
    return RedirectResponse("/profile/" + request.session.get("userid"))

@router.get("/{user_id}")
@csrf_protect
async def profile_of_user_generic(request: Request, user_id: int):
    return await profile_of_user(request, user_id)

async def profile_of_user(request: Request, user_id: int):
    personal = False # Initially
    deleted = await db.fetchval("SELECT deleted FROM users WHERE user_id = $1", user_id)
    if deleted:
        return abort(404)
    user = await get_user(int(user_id))
    if not user:
        return await templates.e(request, "Profile Not Found", 404)
    if "userid" in request.session.keys():
        try:
            guild = client.get_guild(main_server)
            userobj = guild.get_member(int(request.session.get("userid")))
        except:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "Still connecting to Discord. Please refresh in a minute or two"})
        if user_id == int(request.session["userid"]):
            personal = True
        else:
            personal = False
        if userobj is not None and is_staff(staff_roles, userobj.roles, 4)[0]:
            personal = True
    bots = await db.fetch("SELECT DISTINCT bots.bot_id, bots.state FROM bot_owner INNER JOIN bots ON bot_owner.bot_id = bots.bot_id WHERE bot_owner.owner = $1", user_id)
    bot_id_lst = [obj["bot_id"] for obj in bots]
    fetchq = []
    for bid in bot_id_lst:
        base_query = ("SELECT description, banner, state, votes, servers, bot_id, invite FROM bots ")
        if not personal:
            query = base_query + "WHERE bot_id = $1 and (state = 0 OR state = 6) ORDER BY votes"
        else:
            query = base_query + "WHERE bot_id = $1 ORDER BY votes"
        data = await db.fetchrow(query, bid)
        fetchq.append(data)
    user_bots = await parse_bot_list(fetchq)
    if personal:
        user_info = await db.fetchrow("SELECT api_token, badges, description, coins FROM users WHERE user_id = $1", user_id)
    else:
        user_info = await db.fetchrow("SELECT badges, description, coins FROM users  WHERE user_id = $1", user_id)
    if user_info is None:
        return abort(404)
    guild = client.get_guild(main_server)
    user_dpy = guild.get_member(int(user_id))
    if user_dpy is None:
        user_dpy = await client.fetch_user(int(user_id))
    return await templates.TemplateResponse("profile.html", {"request": request, "username": request.session.get("username", False), "user_bots": user_bots, "user": user, "avatar": request.session.get("avatar"), "user_id": user_id, "personal": personal, "badges": get_badges(user_dpy, user_info["badges"], bots), "user_info": user_info, "coins": user_info["coins"]})

