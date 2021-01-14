from ..deps import *

router = APIRouter(
    prefix = "/bot",
    tags = ["Bots"]
)

@router.get("/")
async def bot_rdir(request: Request):
    return RedirectResponse("/")

@router.get("/{bot_id}")
async def bot_index(request: Request, bot_id: int):
    bot = await db.fetchrow("SELECT description, tags, banner, website, certified, votes, servers, bot_id, invite, discord FROM bots WHERE bot_id = $1 ORDER BY votes", bot_id)
    bot_info = await get_bot(bot["bot_id"])
    if bot_info:
        bot_obj = {"bot": bot, "bot_id": bot["bot_id"], "avatar": bot_info["avatar"], "website": bot["website"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"], "support": bot['discord'], "invite": bot["invite"], "tags": bot["tags"]}
    else:
        return abort(404)
    # TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: new_tag.capitalize()})
    form = await Form.from_formdata(request)
    return templates.TemplateResponse("bot.html", {"request": request, "username": request.session.get("username", False), "bot": bot_obj, "tags_fixed": tags_fixed, "form": form, "avatar": request.session.get("avatar")})


@router.get("/description/{bot_id}")
async def bot_desc(request: Request, bot_id: int):
    bot = await db.fetchrow("SELECT long_description FROM bots WHERE bot_id = $1",int(bot_id))
    if bot:
        return templates.TemplateResponse("description.html",{"request":request,"bot":bot})
    else:
        return "Bot not found! :( Try refreshing. After that either report it on the support server or just continue your day!"
