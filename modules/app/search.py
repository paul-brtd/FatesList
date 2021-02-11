from ..deps import *

router = APIRouter(
    prefix = "/search",
    tags = ["Search"],
    include_in_schema = False
)

@router.get("/t")
async def search(request: Request, q: str):
    return await render_search(request = request, q = q, api = False)

@router.get("/tags")
@csrf_protect
async def tags(request: Request, tag: str):
    if tag not in TAGS:
        return RedirectResponse("/")
    fetch = await db.fetch(f"SELECT description, banner,certified,votes,servers,bot_id,tags,invite FROM bots, unnest(tags) a WHERE  lower(a) = '{tag}' AND queue = false and banned = false and disabled = false ORDER BY votes DESC")
    print(fetch)
    search_bots = []
    # TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            search_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})

        # TAGS
    tags_fixed = {}
    for tag in TAGS.keys():
        tag_icon = TAGS[tag]
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: [new_tag.capitalize(), tag_icon]})
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
    if query.replace(" ", "") != "" or debug:
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
