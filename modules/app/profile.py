from ..deps import *

router = APIRouter(
    prefix = "/profile",
    tags = ["Profile"]
)

@router.get("/{userid}")
@csrf_protect
async def profile_of_user(request: Request, userid: int):
    user = await get_user(int(userid))
    if not user:
        return RedirectResponse("/")
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE owner = $1 and queue = false ORDER BY votes", int(userid))
    user_bots = []
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            user_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
    return templates.TemplateResponse("profile.html", {"request": request, "username": request.session.get("username", False), "user_bots": user_bots, "user": user, "avatar": request.session.get("avatar")})

@router.get("/")
@csrf_protect
async def profile(request: Request):
    if "userid" in request.session.keys():
        user = await get_user(int(request.session["userid"]))
        if not user:
            return RedirectResponse("/")
        userid = request.session["userid"]
        fetch = await db.fetch("SELECT description,banner,certified,votes,servers,bot_id,invite FROM bots WHERE owner = $1 and queue = false ORDER BY votes", int(userid))
        user_bots = []
        # TOP VOTED BOTS
        for bot in fetch:
            bot_info = await get_bot(bot["bot_id"])
            if bot_info:
                user_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
        fetch = await db.fetch("SELECT description,banner,certified,votes,servers,bot_id,invite,queue_avatar,queue_username FROM bots WHERE owner = $1 and queue = true", int(userid))
        queue_bots = []
        # TOP VOTED BOTS
        for bot in fetch:
            bot_info = {"username":bot["queue_username"],"avatar":bot["queue_avatar"]}
            if bot_info:
                queue_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"],"queue_bots":queue_bots})
        return templates.TemplateResponse("profile_personal.html", {"request": request, "username": request.session.get("username", False), "user_bots": user_bots, "user": user,"queue_bots":queue_bots, "avatar": request.session.get("avatar")})
    else:
        return RedirectResponse("/")
