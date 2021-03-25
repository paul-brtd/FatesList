from ..deps import *
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

@router.get("/{userid}")
@csrf_protect
async def profile_of_user_generic(request: Request, userid: int):
    return await profile_of_user(request, userid)

async def profile_of_user(request: Request, userid: int):
    personal = False # Initially
    user = await get_user(int(userid))
    if not user:
        return templates.e(request, "Profile Not Found", 404)
    if "userid" in request.session.keys():
        try:
            guild = client.get_guild(main_server)
            userobj = guild.get_member(int(request.session.get("userid")))
        except:
            return templates.TemplateResponse("message.html", {"request": request, "message": "Still connecting to Discord. Please refresh in a minute or two"})
        if userid == int(request.session["userid"]):
            personal = True
        else:
            personal = False
        if userobj is not None and is_staff(staff_roles, userobj.roles, 4)[0]:
            personal = True
    base_query = a = (f"SELECT description, banner, certified, votes, servers, bot_id, invite FROM bots WHERE (owner = {str(userid)} OR {str(userid)} = ANY(extra_owners))")
    if not personal:
        query = base_query + "and queue = false and banned = false and disabled = false ORDER BY votes;"
    else:
        query = base_query + "ORDER BY votes;"
    fetch = await db.fetch(query)
    user_bots = await parse_bot_list(fetch)
    if personal:
        user_info = await db.fetchrow("SELECT api_token, badges, description, certified, coins FROM users WHERE user_id = $1", userid)
    else:
        user_info = await db.fetchrow("SELECT badges, description, certified, coins FROM users  WHERE user_id = $1", userid)
    if user_info is None:
        return abort(404)
    guild = client.get_guild(main_server)
    user_dpy = guild.get_member(int(userid))
    if user_dpy is None:
        user_dpy = await client.fetch_user(int(userid))
    print(user_dpy)
    return templates.TemplateResponse("profile.html", {"request": request, "username": request.session.get("username", False), "user_bots": user_bots, "user": user, "avatar": request.session.get("avatar"), "userid": userid, "personal": personal, "badges": get_badges(user_dpy, user_info["badges"], user_info["certified"]), "user_info": user_info, "coins": user_info["coins"]})

