from ..deps import *

router = APIRouter(
    tags = ["Index"],
    include_in_schema = False
)


@router.get("/")
@csrf_protect
async def home(request: Request):
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false AND banned = false AND disabled = false ORDER BY votes DESC LIMIT 12")
    top_voted = []
    # TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            top_voted.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false AND banned = false AND disabled = false ORDER BY created_at DESC LIMIT 12")
    new_bots = []
    # new bots
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            new_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false and banned = false and disabled = false and certified = true LIMIT 12")
    certified_bots = []
    # certified bots
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            certified_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
        # TAGS
    tags_fixed = {}
    for tag in TAGS.keys():
        tag_icon = TAGS[tag]
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: [new_tag.capitalize(), tag_icon]})
    return templates.TemplateResponse("index.html", {"request": request, "username": request.session.get("username", False), "top_voted": top_voted, "new_bots": new_bots, "certified_bots": certified_bots, "tags_fixed": tags_fixed})

@router.get("/support")
@csrf_protect
async def support(request: Request):
    return RedirectResponse(support_url)

@router.get("/none")
async def nonerouter():
    return RedirectResponse("/static/assets/img/banner.webp", status_code = 301)

@router.get("/v/{vanity}")
@router.get("/{vanity}")
async def vanity_bot(request: Request, vanity: str):
    t = await db.fetchrow("SELECT type, redirect FROM vanity WHERE vanity_url = $1", vanity)
    if t is None:
        return templates.e(request, "Invalid Vanity")
    if t["type"] == 1:
        pre = "/bot/"
    else:
        pre = "/profile/"
    return RedirectResponse(pre + str(t["redirect"]))

@router.get("/feature/{name}")
async def features_view(request: Request, name: str):
    if name not in features.keys():
        return abort(404)
    feature_bots = (f"SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE ('{str(name)}' = ANY(features)) and queue = false and banned = false and disabled = false ORDER BY votes DESC;")
    print(feature_bots)
    bots = await db.fetch(feature_bots)
    bot_obj = []
    for bot in bots:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            bot_obj.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
    return templates.TemplateResponse("feature.html", {"request": request, "name": name, "feature": features[name], "bots": bot_obj})
