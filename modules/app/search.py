from ..deps import *

router = APIRouter(
    prefix = "/search",
    tags = ["Search"],
    include_in_schema = False
)

@router.get("/t")
async def search(request: Request, q: str):
    if q == "":
        return RedirectResponse("/")
    try:
        es = " OR owner = " + str(int(q)) + f" OR {str(q)} = ANY(extra_owners)"
    except:
        es = ""
    desc = ("SELECT bot_id FROM bots WHERE queue = false and banned = false and disabled = false and (description ilike '%" + re.sub(r'\W+|_', ' ', q) + "%'" + es + ")")
    print(desc)
    desc = await db.fetch(desc)
    userc = await db.fetch("SELECT bot_id FROM bot_cache WHERE username ilike '%" + re.sub(r'\W+|_', ' ', q) + "%' and valid_for ilike '%bot%'")
    bids = list(set([id["bot_id"] for id in desc]).union(set([id["bot_id"] for id in userc])))
    print(bids, desc, userc)
    data = str(tuple([int(bid) for bid in bids])).replace("(", "").replace(")", "")
    print("data is " + data)
    if data.replace(" ", "") in ["()", None, ",", ""]:
        fetch = []
    elif data.split(",")[-1].replace(" ", "") == "":
        data = data.replace(",", "")
        fetch = None
    else:
        fetch = None
    if fetch is None:
        abc = ("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false and banned = false and disabled = false and bot_id IN (" + data + ")")
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

    return templates.TemplateResponse("search.html", {"request": request, "username": request.session.get("username", False), "search_bots": search_bots, "tags_fixed": tags_fixed, "avatar": request.session.get("avatar"), "query": q, "profile_search": False})

@router.get("/tags/{tag_search}")
@csrf_protect
async def tags(request: Request, tag_search):
    if tag_search not in TAGS:
        return RedirectResponse("/")
    fetch = await db.fetch(f"SELECT description, banner,certified,votes,servers,bot_id,tags,invite FROM bots, unnest(tags) a WHERE  lower(a) = '{tag_search}' AND queue = false and banned = false and disabled = false ORDER BY votes")
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

    return templates.TemplateResponse("search.html", {"request": request, "username": request.session.get("username", False), "search_bots": search_bots, "tags_fixed": tags_fixed, "avatar": request.session.get("avatar"), "profile_search": False})

@router.get("/profile")
async def profile_search(request: Request, q: Optional[str] = None):
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: new_tag.capitalize()})
    if q is None:
        query = ""
    else:
        query = q
    try:
        es = " OR userid = " + str(int(query))
    except:
        es = ""
    debug = False
    if query != "" or debug:
        profiles = "SELECT userid, description, certified FROM users" # Base profile
        if query != "":
            profiles = profiles + (" WHERE (username ilike '%" + re.sub(r'\W+|_', ' ', query) + "%'" + es + ")")
        print(profiles)
        profiles = await db.fetch(profiles)
        print(profiles)
    else:
        profiles = []
    profile_obj = []
    for profile in profiles:
        profile_info = await get_user(profile["userid"])
        print(profile_info)
        if profile_info:
            profile_obj.append({"user": profile, "avatar": profile_info["avatar"], "username": profile_info["username"], "description": profile["description"], "certified": profile["certified"] == True})
    return templates.TemplateResponse("search.html", {"request": request, "tags_fixed": tags_fixed, "profile_search": True, "query": query, "profiles": profile_obj})
