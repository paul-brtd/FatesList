from ..deps import *

router = APIRouter(
    tags = ["Index"],
    include_in_schema = False
)


@router.get("/")
@csrf_protect
async def home(request: Request):
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false ORDER BY votes DESC LIMIT 12")
    top_voted = []
    # TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            top_voted.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false ORDER BY created_at DESC LIMIT 12")
    new_bots = []
    # new bots
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            new_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false and certified = true LIMIT 12")
    certified_bots = []
    # certified bots
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            certified_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
        # TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: new_tag.capitalize()})

    return templates.TemplateResponse("index.html", {"request": request, "username": request.session.get("username", False), "top_voted": top_voted, "new_bots": new_bots, "certified_bots": certified_bots, "tags_fixed": tags_fixed, "avatar": request.session.get("avatar")})

@router.get("/support")
@csrf_protect
async def support(request: Request):
    return RedirectResponse(support_url)
