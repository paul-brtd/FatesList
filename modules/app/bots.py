from ..deps import *

router = APIRouter(
    prefix = "/bot",
    tags = ["Bots"],
    include_in_schema = False
)

@router.get("/")
async def bot_rdir(request: Request):
    return RedirectResponse("/")

@router.get("/{bot_id}")
async def bot_index(request: Request, bot_id: int):
    bot = await db.fetchrow("SELECT prefix, shard_count, queue, description, bot_library AS library, tags, banner, website, certified, votes, servers, bot_id, invite, discord, owner, extra_owners, banner, api_token, banned, disabled, github FROM bots WHERE bot_id = $1 ORDER BY votes", bot_id)
    if bot is None:
        return templates.e(request, "Bot Not Found")
    if bot["extra_owners"] is None:
        eo = []
    else:
        eo = bot["extra_owners"]
    if "userid" in request.session.keys():
        guild = client.get_guild(builtins.reviewing_server)
        user = guild.get_member(int(request.session.get("userid")))
        if bot["owner"] == int(request.session["userid"]) or int(request.session["userid"]) in eo or (user is not None and is_staff(staff_roles, user.roles, 4)[0]):
            bot_admin = True
        else:
            bot_admin = False
    else:
        bot_admin = False
    img_header_list = ["image/gif", "image/png", "image/jpeg", "image/jpg"]
    banner = bot["banner"].replace(" ", "%20").replace("\n", "")
    try:
        res = await requests.get(banner)
        if response.headers['Content-Type'] not in header_list:
            banner = "none"
    except:
        banner = "none"

    bot_info = await get_bot(bot["bot_id"])
    guild = client.get_guild(reviewing_server)
    events = await get_normal_events(bot["bot_id"])
    maint = await in_maint(bot["bot_id"])
    ed = [((await get_user(id)), id) for id in eo]
    if bot_info:
        bot_obj = {"bot": bot, "bot_id": bot["bot_id"], "avatar": bot_info["avatar"], "website": bot["website"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"], "support": bot['discord'], "invite": bot["invite"], "tags": bot["tags"], "library": bot['library'], "banner": banner, "token": bot["api_token"], "shards": await human_format(bot["shard_count"]), "owner": bot["owner"], "owner_pretty": await get_user(bot["owner"]), "banned": bot['banned'], "disabled": bot['disabled'], "prefix": bot["prefix"], "github": bot['github'], "extra_owners": ed, "leo": len(ed), "queue": bot["queue"]}
    else:
        return templates.e(request, "Bot Not Found")
    # TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: new_tag.capitalize()})
    form = await Form.from_formdata(request)
    ws_events.append((bot_id, {"type": "view", "event_id": None, "event": "view", "context": "user=0::hidden=1"}))
    return templates.TemplateResponse("bot.html", {"request": request, "username": request.session.get("username", False), "bot": bot_obj, "tags_fixed": tags_fixed, "form": form, "avatar": request.session.get("avatar"), "events": events, "maint": maint, "bot_admin": bot_admin})


@router.get("/description/{bot_id}")
async def bot_desc(request: Request, bot_id: int):
    bot = await db.fetchrow("SELECT long_description FROM bots WHERE bot_id = $1",int(bot_id))
    if bot:
        return templates.TemplateResponse("description.html",{"request":request,"bot":bot})
    else:
        return "Bot not found! :( Try refreshing. After that either report it on the support server or just continue your day!"

