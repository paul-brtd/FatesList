"""
Handles rendering of bots, index, search and profile search etc.
"""

import bleach
from lxml.html.clean import Cleaner

from .events import *
from .helpers import *
from .imports import *
from .permissions import *
from .reviews import *
from .templating import *

cleaner = Cleaner()

async def render_index(request: Request, api: bool):
    top_voted = await do_index_query(add_query = "ORDER BY votes DESC", state = [0])
    new_bots = await do_index_query(add_query = "ORDER BY created_at DESC", state = [0]) # and certified = true ORDER BY votes
    certified_bots = await do_index_query(add_query = "ORDER BY votes DESC", state = [6]) # State 6 is certified
    base_json = {
        "tags_fixed": tags_fixed, 
        "top_voted": top_voted, 
        "new_bots": new_bots, 
        "certified_bots": certified_bots, 
        "roll_api": "/api/bots/random"
    }
    if not api:
        return await templates.TemplateResponse("index.html", {"request": request, "random": random} | base_json)
    else:
        return base_json

#@jit(nopython = True)
def gen_owner_html(owners_lst: tuple):
    """Generate the owner html"""
    first_done = False
    last_done = False
    # First owner will always be main and hence should have the crown
    owners_html = '<span class="iconify" data-icon="mdi-crown" data-inline="false"></span>'
    owners_html += "<br/>".join([f"<a class='long-desc-link' href='/profile/{owner[0]}'>{owner[1]}</a>" for owner in owners_lst if owner]
    return owners_html

async def render_bot(request: Request, bt: BackgroundTasks, bot_id: int, api: bool, rev_page: int = 1):
    if bot_id >= 9223372036854775807: # Max size of bigint
        return abort(404)
    bot = await db.fetchrow(
        """SELECT js_allowed, prefix, shard_count, state, description, bot_library AS library, 
        banner, website, votes, servers, bot_id, discord AS support, banner, github, features, 
        invite_amount, css, long_description_type, long_description, donate, privacy_policy, 
        nsfw FROM bots WHERE bot_id = $1""", 
        bot_id
    )
    tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
    if not bot or not tags:
        if api:
            return abort(404) # If API, just regular 404 JSON
        return await templates.e(
            request, 
            "It might still be in our RabbitMQ queue waiting to be added to our database if you recently added it. Try reloading!",
            main = "Bot Not Found"
        ) # Otherwise HTML error
    bot = dict(bot) | {"tags": [tag["tag"] for tag in tags]}
                             
    # Get all bot owners
    owners = await db.fetch(
        "SELECT DISTINCT ON (owner) owner, main FROM bot_owner WHERE bot_id = $1 ORDER BY owner, main DESC", 
        bot_id
    )
    _owners = []
    for owner in owners:
        if owner["main"]: _owners.insert(0, owner)
        else: _owners.append(owner)
    owners = _owners
    bot["description"] = intl_text(bot['description'], request.session.get("site_lang", "default"))   
    bot['long_description'] = intl_text(bot['long_description'], request.session.get("site_lang", "default"))
    if bot["long_description_type"] == enums.LongDescType.markdown_pymarkdown: # If we are using markdown
        ldesc = emd(markdown.markdown(bot['long_description'], extensions = md_extensions))
    else: 
        ldesc = bot['long_description']

    user_js_allowed = request.session.get("js_allowed", True)
    if not user_js_allowed or not bot["js_allowed"]:
        try:
            ldesc = cleaner.clean_html(ldesc)
        except:
            ldesc = bleach.clean(ldesc)

        # Take the h1...h5 anad drop it one lower and fix peoples stupidity and some nice patches to the site to improve accessibility
    long_desc_replace_tuple = (
        ("<h1", "<h2 style='text-align: center'"), 
        ("h2", "h3"),
        ("h4", "h5"),
        ("h6", "p"),
        ("<a", "<a class='long-desc-link ldlink'"), 
        ("<!DOCTYPE", ""), 
        ("html>", ""), 
        ("<body", ""), 
        ("div", "article"), 
        (".click", ""),
        ("bootstrap.min.css", ""),
        ("bootstrap.css", ""), 
        ("jquery.min.js", ""), 
        ("jquery.js", ""), 
        ("fetch(", "")
    )
    ldesc = ireplacem(long_desc_replace_tuple, ldesc)

    if "user_id" in request.session.keys():
        bot_admin = await is_bot_admin(int(bot_id), int(request.session.get("user_id"))) 
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
        bot_features = ""
    else:
        bot_features = "<br/>".join([f"<a class='long-desc-link' href='/feature/{feature}'>{features[feature]['name']}</a>" for feature in bot["features"]])
    
    if bot_info:
        bot = dict(bot)
        user = await get_bot(bot_id)
        user["name"] = user["username"]
        bot_extra = {
            "votes": human_format(bot["votes"]), 
            "servers": human_format(bot["servers"]),
            "banner": ireplacem(banner_replace_tuple, banner),
            "shards": human_format(bot["shard_count"]), 
            "owners_html": owners_html, 
            "features": bot_features,
            "long_description": ireplacem(ldesc_replace_tuple, ldesc),
            "info": user, 
            "long_description_type": bot["long_description_type"]
        }
        bot |= bot_extra
    
    else:
        return await templates.e(request, "Bot Not Found")
    
    _tags_fixed_bot = [tag for tag in tags_fixed if tag["id"] in bot["tags"]]
    bt.add_task(add_ws_event, bot_id, {"m": {"e": enums.APIEvents.bot_view}, "ctx": {"user": request.session.get('user_id'), "widget": False}})
    reviews = await parse_reviews(bot_id, page = rev_page)
    
    context = {
        "id": str(bot_id), 
        "bot_token": bot["api_token"] if bot["api_token"] else None,
        "type": "bot",
        "bot_admin": bot_admin,
        "reviews": {
            "average_rating": float(reviews[1])
        }
    }
    
    data = {
        "data": bot, 
        "type": "bot", 
        "id": bot_id, 
        "tags_fixed": _tags_fixed_bot, 
        "promos": promos, 
        "maint": maint, 
        "admin": bot_admin, 
        "guild": main_server, 
        "bot_reviews": reviews[0], 
        "average_rating": reviews[1], 
        "total_reviews": reviews[2], 
        "review_page": rev_page, 
        "total_review_pages": reviews[3], 
        "per_page": reviews[4]
    }

    if not api:
        return await templates.TemplateResponse("bot_server.html", {"request": request, "replace_last": replace_last} | data, context = context)
    else:
        data["bot_id"] = str(bot_id)
        return data

async def render_bot_widget(request: Request, bt: BackgroundTasks, bot_id: int, api: bool):
    bot = await db.fetchrow("SELECT bot_id, servers, votes FROM bots WHERE bot_id = $1", bot_id)
    if not bot:
        if api:
            return abort(404)
        return "No Bot Found, cannot display widget"
    bot = dict(bot)
    bot["votes"] = human_format(bot["votes"])
    bot["servers"] = human_format(bot["servers"])
    bt.add_task(add_ws_event, bot_id, {"m": {"e": enums.APIEvents.bot_view}, "ctx": {"user": request.session.get('user_id'), "widget": True}})
    data = {"bot": bot, "user": await get_bot(bot_id)}
    if api:
        return data
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
        profiles = await db.fetch(
            """SELECT DISTINCT users.user_id, users.description FROM users 
            INNER JOIN bot_owner ON users.user_id = bot_owner.owner 
            INNER JOIN bots ON bot_owner.bot_id = bots.bot_id 
            WHERE ((bots.state = 0 OR bots.state = 6) 
            AND (bots.username_cached ilike $1 OR bots.description ilike $1 OR bots.bot_id::text ilike $1)) 
            OR (users.username ilike $1) LIMIT 12
            """, f'%{q}%'
        )
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

async def render_server(request: Request, guild_id: int, bt: BackgroundTasks, **kwargs):
    guild = client_servers.get_guild(guild_id)
    if not guild:
        return abort(404)
    guild_data = await db.fetchrow("SELECT description, long_description from servers WHERE guild_id = $1", guild_id)
    if not guild_data:
        return await templates.e(request, "Ask a server manager or admin to add this server to finish adding this server to our list!")
    bt.add_task(add_ws_event, guild_id, {"m": {"e": enums.APIEvents.server_view}, "ctx": {"user": request.session.get('user_id'), "widget": False}}, type = "server")
    data = {"data": guild_data | {"name": guild.name}, "type": "server", "id": guild_id, "tags_fixed": []} # TODO: Add tags, reviews and voting
    return await templates.TemplateResponse("bot_server.html", {"request": request, "replace_last": replace_last} | data)
