from ..deps import *
from ..badges import *

router = APIRouter(
    prefix = "/profile",
    tags = ["Profile"],
    include_in_schema = False
)

@router.get("/me")
@csrf_protect
async def profile(request: Request):
    if "userid" in request.session.keys():
        user = await get_user(int(request.session["userid"]))
        if not user:
            return RedirectResponse("/")
        return await profile_of_user(request, int(request.session["userid"]))
    else:
        return RedirectResponse("/")

@router.get("/{userid}")
@csrf_protect
async def profile_of_user(request: Request, userid: int):
    user = await get_user(int(userid))
    if not user:
        return templates.e(request, "Profile Not Found", 404)
    a = (f"SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE (owner = {str(userid)} OR {str(userid)} = ANY(extra_owners)) and queue = false and banned = false and disabled = false ORDER BY votes;")
    fetch = await db.fetch(a)
    if "userid" in request.session.keys():
        guild = client.get_guild(builtins.reviewing_server)
        userobj = guild.get_member(int(request.session.get("userid")))
        personal = False
        try:
            if userid == int(request.session["userid"]):
                personal = True
            if userid == int(request.session["userid"]) or (userobj is not None and is_staff(staff_roles, userobj.roles, 4)[0]):
                bot_admin = True
            else:
                bot_admin = False
        except:
            if userid == int(request.session["userid"]):
                bot_admin = True
            else:
                bot_admin = False
    else:
        bot_admin = False
        personal = False
    user_bots = []
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            user_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
    user_info = await db.fetchrow("SELECT badges, description, certified FROM users WHERE userid = $1", userid)
    if user_info is None:
        return RedirectResponse("/profile/404")
    guild = client.get_guild(reviewing_server)
    user_dpy = guild.get_member(int(userid))
    if user_dpy is None:
        user_dpy = await client.fetch_user(int(userid))
    print(user_dpy)
    return templates.TemplateResponse("profile.html", {"request": request, "username": request.session.get("username", False), "user_bots": user_bots, "user": user, "avatar": request.session.get("avatar"), "admin": bot_admin, "userid": userid, "personal": personal, "badges": get_badges(user_dpy, user_info["badges"], user_info["certified"] == True)})

@router.get("/{userid}/edit")
async def profile_editor(request: Request, userid: int):
    if request.session.get("userid") is None:
        return RedirectResponse("/")
    guild = client.get_guild(builtins.reviewing_server)
    userobj = guild.get_member(int(request.session.get("userid")))
    admin = False
    staff = False
    if userobj is None:
        if userid == int(request.session.get("userid")):
            admin = True
        else:
            admin = False
    elif admin or (is_staff(staff_roles, userobj.roles, 4)[0] or userid == int(request.session.get("userid"))):
        admin = True
        staff = True
    else:
        pass
    if not admin:
        return RedirectResponse("/")
    data = await db.fetchrow("SELECT token, description, certified, badges FROM users WHERE userid = $1", userid)
    vanity = await db.fetchrow("SELECT vanity_url AS vanity FROM vanity WHERE redirect = $1", userid)
    if vanity is None:
        vanity = {"vanity": None}
    return templates.TemplateResponse("profile_edit.html", {"request": request, "token": data["token"], "certified": data["certified"] == True, "fstaff": staff, "vanity": vanity["vanity"], "form": await Form.from_formdata(request)})
