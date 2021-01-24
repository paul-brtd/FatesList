from ..deps import *

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
        userid = request.session["userid"]
        try:
            userid = int(userid)
        except:
            return RedirectResponse("/")
        fetch = await db.fetch(f"SELECT banned,description,banner,certified,votes,servers,bot_id,invite FROM bots WHERE (owner = {str(userid)} OR {str(userid)} = ANY(extra_owners)) and queue = false ORDER BY votes")
        user_bots = []
        # TOP VOTED BOTS
        for bot in fetch:
            bot_info = await get_bot(bot["bot_id"])
            if bot_info:
                user_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"], "banned": bot['banned']})
        fetch = await db.fetch("SELECT banned,description,banner,certified,votes,servers,bot_id,invite FROM bots WHERE owner = $1 and queue = true", int(userid))
        queue_bots = []
        # TOP VOTED BOTS
        for bot in fetch:
            bot_info = await get_bot(bot["bot_id"])
            if bot_info is None:
                continue
            bot_info = {"username":bot_info["username"],"avatar":bot_info["avatar"]}
            if bot_info:
                queue_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"],"banned": bot['banned']})
        return templates.TemplateResponse("profile_personal.html", {"request": request, "username": request.session.get("username", False), "user_bots": user_bots, "user": user,"queue_bots":queue_bots, "avatar": request.session.get("avatar")})
    else:
        return RedirectResponse("/")

@router.get("/{userid}")
@csrf_protect
async def profile_of_user(request: Request, userid: int):
    user = await get_user(int(userid))
    if not user:
        return RedirectResponse("/")
    a = (f"SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE (owner = {str(userid)} OR {str(userid)} = ANY(extra_owners)) and queue = false and banned = false and disabled = false ORDER BY votes;")
    fetch = await db.fetch(a)
    if "userid" in request.session.keys():
        guild = client.get_guild(builtins.reviewing_server)
        userobj = guild.get_member(int(request.session.get("userid")))
        if userid == int(request.session["userid"]) or (userobj is not None and is_staff(staff_roles, userobj.roles, 4)[0]):
            bot_admin = True
        else:
            bot_admin = False
    else:
        bot_admin = False
    user_bots = []
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            user_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
    return templates.TemplateResponse("profile.html", {"request": request, "username": request.session.get("username", False), "user_bots": user_bots, "user": user, "avatar": request.session.get("avatar"), "admin": bot_admin, "userid": userid})

@router.get("/me/edit")
async def profile_editor(request: Request):
    if request.session.get("userid") is None:
        return RedirectResponse("/")
    data = await db.fetchrow("SELECT token, description, certified, vanity, badges FROM users WHERE userid = $1", int(request.session.get("userid")))
    return templates.TemplateResponse("profile_edit.html", {"request": request, "token": data["token"], "certified": data["certified"] == True})
