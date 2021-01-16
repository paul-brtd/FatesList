from ..deps import *

router = APIRouter(
    prefix = "/search",
    tags = ["Search"]
)

@router.get("/t")
async def search(request: Request, q: str):
    desc = await db.fetch("SELECT bot_id FROM bots WHERE queue = false and (description ilike '%" + re.sub(r'\W+|_', ' ', q) + "%')")
    userc = await db.fetch("SELECT bot_id FROM bot_cache WHERE username ilike '%" + re.sub(r'\W+|_', ' ', q) + "%' and valid_for ilike '%bot%'")
    bids = list(set([id["bot_id"] for id in desc]).union(set([id["bot_id"] for id in userc])))
    print(bids, desc, userc)
    abc = ("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false and bot_id IN " + str(tuple([int(bid) for bid in bids])))
    print(abc)
    fetch = await db.fetch(abc)
    search_bots = []
    # TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            search_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})

        # TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: new_tag.capitalize()})

    return templates.TemplateResponse("search.html", {"request": request, "username": request.session.get("username", False), "search_bots": search_bots, "tags_fixed": tags_fixed, "avatar": request.session.get("avatar")})

@router.get("/tags/{tag_search}")
@csrf_protect
async def tags(request: Request, tag_search):
    if tag_search not in TAGS:
        return RedirectResponse("/")
    fetch = await db.fetch(f"SELECT description, banner,certified,votes,servers,bot_id,tags,invite FROM bots, unnest(tags) a WHERE  lower(a) = '{tag_search}' ORDER BY votes")
    print(fetch)
    search_bots = []
    # TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            search_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})

        # TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: new_tag.capitalize()})

    return templates.TemplateResponse("search.html", {"request": request, "username": request.session.get("username", False), "search_bots": search_bots, "tags_fixed": tags_fixed, "avatar": request.session.get("avatar")})
