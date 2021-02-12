from ..deps import *

router = APIRouter(
    tags = ["Index"],
    include_in_schema = False
)


@router.get("/")
async def index_fend(request: Request):
    return await render_index(request = request, api = False)


@router.get("/none")
async def nonerouter():
    return RedirectResponse("/static/assets/img/banner.webp", status_code = 301)

async def vanity_bot(vanity: str):
    t = await db.fetchrow("SELECT type, redirect FROM vanity WHERE vanity_url = $1", vanity)
    if t is None:
        return None
    if t["type"] == 1:
        type = "bot"
    else:
        type = "profile"
    return "/" + type + "/" + str(t["redirect"]), type

@router.get("/{vanity}")
async def vanity_bot_uri(request: Request, vanity: str):
    vurl = await vanity_bot(vanity)
    if vurl is None:
        return templates.e(request, "Invalid Vanity")
    return RedirectResponse(vurl[0])

@router.get("/{vanity}/edit")
async def vanity_edit(request: Request, vanity: str):
    vurl = await vanity_bot(vanity)
    if vurl is None:
        return templates.e(request, "Invalid Vanity")
    if vurl[1] == "profile":
        return abort(404)
    return RedirectResponse(vurl[0] + "/edit")

@router.get("/{vanity}/vote")
async def vanity_vote(request: Request, vanity: str):
    vurl = await vanity_bot(vanity)
    if vurl is None:
        return templates.e(request, "Invalid Vanity")
    if vurl[1] == "profile":
        return abort(404)
    return RedirectResponse(vurl[0] + "/vote")

@router.get("/{vanity}/invite")
async def vanity_invite(request: Request, vanity: str):
    vurl = await vanity_bot(vanity)
    if vurl is None:
        return templates.e(request, "Invalid Vanity")
    if vurl[1] == "profile":
        return abort(404)
    return RedirectResponse(vurl[0] + "/invite")

@router.get("/v/{a:path}")
async def v_legacy(request: Request, a: str):
    return RedirectResponse(str(request.url).replace("/v/", "/"))

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
            bot_obj.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": human_format(bot["votes"]), "servers": human_format(bot["servers"]), "description": bot["description"]})
    return templates.TemplateResponse("feature.html", {"request": request, "name": name, "feature": features[name], "bots": bot_obj})

