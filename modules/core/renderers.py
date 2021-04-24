"""
Handles rendering of bots, index, search and profile search etc.
"""

from .imports import *
from .permissions import *
from .helpers import *
from .templating import *
from .events import *
from .reviews import *

async def render_index(request: Request, api: bool):
    top_voted = await do_index_query(add_query = "ORDER BY votes")
    new_bots = await do_index_query(add_query = "ORDER BY created_at") # and certified = true ORDER BY votes
    certified_bots = await do_index_query(add_query = "ORDER BY votes", state = 6) # State 6 is certified
    base_json = {"tags_fixed": tags_fixed, "top_voted": top_voted, "new_bots": new_bots, "certified_bots": certified_bots, "roll_api": "/api/bots/random"}
    if not api:
        return await templates.TemplateResponse("index.html", {"request": request, "random": random} | base_json)
    else:
        return base_json

#@jit(nopython = True)
def gen_owner_html(owners_lst: tuple):
    """
    Generate the owner html, this is JIT'd for better performance
    """
    first_done = False
    last_done = False
    owners_html = ""
    for i in range(0, len(owners_lst)):
        owner = owners_lst[i]
        if owner is None: 
            continue
        if last_done:
            owners_html += " and "
        elif first_done:
            owners_html += ", "
        owners_html += "<a class='long-desc-link' href='/profile/" + owner[0] + "'>" + owner[1] + "</a>"
        if i >= len(owners_lst) - 2: # Twi to get last guy
            last_done = True
        else:
            first_done = True
    return owners_html

async def render_bot(request: Request, bt: BackgroundTasks, bot_id: int, api: bool):
    
    bot = await db.fetchrow("SELECT prefix, shard_count, state, description, bot_library AS library, banner, website, votes, servers, bot_id, discord AS support, banner, github, features, invite_amount, css, long_description_type, long_description, donate, privacy_policy, nsfw FROM bots WHERE bot_id = $1", bot_id)
    tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
    if not bot or not tags:
        if api:
            return abort(404) # If API, just regular 404 JSON
        return await templates.e(request, "It might still be in our RabbitMQ queue waiting to be added to our database if you recently added it. Try reloading!", main = "Bot Not Found") # Otherwise HTML error
    bot = dict(bot) | {"tags": [tag["tag"] for tag in tags]}
    owners = await db.fetch("SELECT owner FROM bot_owner WHERE bot_id = $1", bot_id) # Get all bot owners

    if bot["long_description_type"] == enums.LongDescType.markdown_pymarkdown: # If we are using markdown
        ldesc = emd(markdown.markdown(bot['long_description'], extensions=["extra", "abbr", "attr_list", "def_list", "fenced_code", "footnotes", "tables", "admonition", "codehilite", "meta", "nl2br", "sane_lists", "toc", "wikilinks", "smarty", "md_in_html"]))
    else:
        ldesc = bot['long_description']

        # Take the h1...h5 anad drop it one lower and fix peoples stupidity and some nice patches to the site to improve accessibility
    long_desc_replace_tuple = (("<h1", "<h2 style='text-align: center'"), ("h2", "h3"), ("h4", "h5"), ("h6", "p"), ("<a", "<a class='long-desc-link ldlink'"), ("<!DOCTYPE", ""), ("html>", ""), ("<body", ""), ("div", "article"), (".click", ""), ("bootstrap.min.css", ""), ("bootstrap.css", ""), ("jquery.min.js", ""), ("jquery.js", ""), ("fetch(", ""))
    ldesc = ireplacem(long_desc_replace_tuple, ldesc)

    if "userid" in request.session.keys():
        bot_admin = await is_bot_admin(int(bot_id), int(request.session.get("userid"))) 
    else:
        bot_admin = False
    if not bot_admin:
        bot["api_token"] = None
    else:
        bot["api_token"] = await db.fetchval("SELECT api_token FROM bots WHERE bot_id = $1", bot_id)

    if bot["banner"]:
        banner = bot["banner"].replace(" ", "%20").replace("\n", "")
    else:
        banner = ""

    bot_info = await get_bot(bot["bot_id"])
    
    promos = await get_promotions(bot["bot_id"])
    maint = await get_maint(bot["bot_id"])

    owners_lst = tuple([(await get_user(obj["owner"], user_only = True)) for obj in owners if obj["owner"] is not None])
    owners_html = gen_owner_html(owners_lst)
    if bot["features"] is None:
        features = []
    else:
        features = bot["features"]
    
    bot_features = ", ".join([f"<a class='long-desc-link' href='/feature/{feature}'>{feature.replace('_', ' ').title()}</a>" for feature in features])
    if len(features) > 1:
        bot_features = replace_last(bot_features, ",", " and")
    if bot_info:
        bot = dict(bot)
        bot = bot | {"votes": human_format(bot["votes"]), "servers": human_format(bot["servers"]), "banner": banner.replace("\"", "").replace("'", "").replace("http://", "https://").replace("(", "").replace(")", "").replace("file://", ""), "shards": human_format(bot["shard_count"]), "owners_html": owners_html, "features": bot_features, "long_description": ldesc.replace("window.location", "").replace("document.ge", ""), "user": (await get_bot(bot_id)), "long_description_type": bot["long_description_type"]}
        #await db.execute("UPDATE bots SET username_cached = $2 WHERE bot_id = $1", int(bot_id), bot_info["username"])   
    else:
        return await templates.e(request, "Bot Not Found")
    _tags_fixed_bot = [tag for tag in tags_fixed if tag["id"] in bot["tags"]]
    form = await Form.from_formdata(request)
    bt.add_task(bot_add_ws_event, bot_id, {"payload": "event", "id": str(uuid.uuid4()), "event": "view_bot", "context": {"user": request.session.get('userid'), "widget": False}})
    reviews = await parse_reviews(bot_id)
    data = {"bot": bot, "bot_id": bot_id, "tags_fixed": _tags_fixed_bot, "promos": promos, "maint": maint, "bot_admin": bot_admin, "guild": main_server, "botp": True, "bot_reviews": reviews[0], "average_rating": reviews[1]}

    if not api:
        return await templates.TemplateResponse("bot.html", {"request": request, "form": Form, "replace_last": replace_last} | data)
    else:
        data["bot_id"] = str(bot_id)
        return data

async def render_bot_widget(request: Request, bt: BackgroundTasks, bot_id: int, api: bool):
    bot = await db.fetchrow("SELECT bot_id, servers, votes FROM bots WHERE bot_id = $1", bot_id)
    if not bot:
        if api:
            return abort(404)
        return "No Bot Found, cannot display wifget"
    bot = dict(bot)
    bot["votes"] = human_format(bot["votes"])
    bot["servers"] = human_format(bot["servers"])
    bt.add_task(bot_add_ws_event, bot_id, {"payload": "event", "id": str(uuid.uuid4()), "event": "view_bot", "context": {"user": request.session.get('userid'), "widget": True}})
    data = {"bot": bot, "user": await get_bot(bot_id)}
    return await templates.TemplateResponse("widget.html", {"request": request} | data)

async def render_search(request: Request, q: str, api: bool):
    if q == "":
        if api:
            return abort(404)
        else:
            return RedirectResponse("/")
    bots = await db.fetch("SELECT DISTINCT bots.bot_id, bots.state, bots.banner, bots.votes, bots.servers, bots.description, bots.invite, bots.nsfw FROM bots INNER JOIN bot_owner ON bots.bot_id = bot_owner.bot_id WHERE (bots.state = 0 OR bots.state = 6) and (bots.description ilike $1 OR bots.username_cached ilike $1 OR bot_owner.owner::text ilike $1) ORDER BY bots.votes LIMIT 6", f'%{q}%')
    search_bots = await parse_index_query(bots)
    if not api:
        return await templates.TemplateResponse("search.html", {"request": request, "search_bots": search_bots, "tags_fixed": tags_fixed, "query": q, "profile_search": False})
    else:
        return {"search_bots": search_bots, "tags_fixed": tags_fixed, "query": q, "profile_search": False}

async def render_profile_search(request: Request, q: str, api: bool):
    if q == "" or q is None:
        if api:
            return abort(404)
        else:
            q = ""
    if q.replace(" ", "") != "":
        profiles = await db.fetch("SELECT DISTINCT users.user_id, users.description FROM users INNER JOIN bot_owner ON users.user_id = bot_owner.owner INNER JOIN bots ON bot_owner.bot_id = bots.bot_id WHERE ((bots.state = 0 OR bots.state = 6) AND (bots.username_cached ilike $1 OR bots.description ilike $1 OR bots.bot_id::text ilike $1)) OR (users.username ilike $1) AND users.state != $2 LIMIT 12", f'%{q}%', enums.UserState.ddr_ban)
    else:
        profiles = []
    profile_obj = []
    for profile in profiles:
        profile_info = await get_user(profile["user_id"])
        if profile_info:
            profile_obj.append({"banner": None, "description": profile["description"]}| profile_info)
    if not api:
        return await templates.TemplateResponse("search.html", {"request": request, "tags_fixed": tags_fixed, "profile_search": True, "query": q, "profiles": profile_obj})
    else:
        return {"profiles": profile_obj, "tags_fixed": tags_fixed, "query": q, "profile_search": True}
