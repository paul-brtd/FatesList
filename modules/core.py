"""
Core functions of Fates List. 

TODO: Finish documenting all core functions
TODO: Move uncertify into BotListAdmin class
TODO: Move delete_bot to BotActions class
"""

from modules.corelib import *

# FastAPI Limiter rl func
async def rl_key_func(request: Request) -> str:
    if request.headers.get("FatesList-RateLimitBypass") == ratelimit_bypass_key: # Check ratelimit key
        return get_token(32) # Disable
    if "Authorization" in request.headers or "authorization" in request.headers:
        try: # Check for auth header
            r = request.headers["Authorization"]
        except KeyError:
            r = request.headers["authorization"]
        check = await db.fetchrow("SELECT bot_id, state FROM bots WHERE api_token = $1", r) # Check api token
        if check is None:
            return ip_check(request) # Invalid api token, fallback to ip
        if check["state"] == enums.BotState.certified:
            return get_token(32) # Disable since certified bots are exempt
        return str(check["bot_id"]) # Otherwise, ratelimit using bot id
    else:
        return ip_check(request) # Fallback to ip

#CREATE TABLE bot_stats_votes (
#   bot_id bigint,
#   total_votes bigint
#); 

#CREATE TABLE bot_stats_votes_pm (
#   bot_id bigint,
#   epoch bigint,
#   votes bigint
#);

async def parse_reviews(bot_id: int, reviews: List[asyncpg.Record] = None) -> List[dict]:
    if reviews is None:
        _rev = True
        reviews = await db.fetch("SELECT id, reply, user_id, star_rating, review_text AS review, review_upvotes, review_downvotes, flagged, epoch, replies AS _replies FROM bot_reviews WHERE bot_id = $1 AND reply = false ORDER BY epoch, star_rating ASC", bot_id)
    else:
        _rev = False
    i = 0
    stars = 0
    while i < len(reviews):
        reviews[i] = dict(reviews[i])
        if reviews[i]["epoch"] in ([], None):
            reviews[i]["epoch"] = [time.time()]
        else:
            reviews[i]["epoch"].sort(reverse = True)
        reviews[i]["time_past"] = str(time.time() - reviews[i]["epoch"][0])
        reviews[i]["epoch"] = [str(ep) for ep in reviews[i]["epoch"]]
        reviews[i]["id"] = str(reviews[i]["id"])
        reviews[i]["user"] = await get_user(reviews[i]["user_id"])
        reviews[i]["user_id"] = str(reviews[i]["user_id"])
        reviews[i]["star_rating"] = round(reviews[i]["star_rating"], 2)
        reviews[i]["replies"] = []
        reviews[i]["review_upvotes"] = [str(ru) for ru in reviews[i]["review_upvotes"]]
        reviews[i]["review_downvotes"] = [str(rd) for rd in reviews[i]["review_downvotes"]]
        if _rev:
            stars += reviews[i]["star_rating"]
        for review_id in reviews[i]["_replies"]:
            _reply = await db.fetch("SELECT id, reply, user_id, star_rating, review_text AS review, review_upvotes, review_downvotes, flagged, epoch, replies AS _replies FROM bot_reviews WHERE id = $1", review_id)
            _parsed_reply = await parse_reviews(bot_id, _reply)
            try:
                reviews[i]["replies"].append(_parsed_reply[0][0])
            except:
                pass
        del reviews[i]["_replies"]
        i+=1
    if i == 0:
        return reviews, 10.0
    return reviews, round(stars/i, 2)

# Get Bots Helper
async def render_bot(request: Request, bt: BackgroundTasks, bot_id: int, review: bool, widget: bool):
    guild = client.get_guild(main_server)
    try:
        bot = dict(await db.fetchrow("SELECT js_whitelist, api_token, prefix, shard_count, state, description, bot_library AS library, tags, banner, website, votes, servers, bot_id, discord AS support, banner, github, features, invite_amount, css, html_long_description AS html_ld, long_description, donate, privacy_policy, nsfw FROM bots WHERE bot_id = $1", bot_id))
    except:
        return await templates.e(request, "Bot Not Found")
    owners = await db.fetch("SELECT owner FROM bot_owner WHERE bot_id = $1", bot_id)
    if bot is None:
        return await templates.e(request, "Bot Not Found")
    if not bot["html_ld"]:
        ldesc = emd(markdown.markdown(bot['long_description'], extensions=["extra", "abbr", "attr_list", "def_list", "fenced_code", "footnotes", "tables", "admonition", "codehilite", "meta", "nl2br", "sane_lists", "toc", "wikilinks", "smarty", "md_in_html"]))
    else:
        ldesc = bot['long_description']
    # Take the h1...h5 anad drop it one lower
    ldesc = ldesc.replace("<h1", "<h2 style='text-align: center'").replace("<h2", "<h3").replace("<h4", "<h5").replace("<h6", "<p")

    if widget:
        bot_admin = False
    else:
        if "userid" in request.session.keys():
            bot_admin = await is_bot_admin(int(bot_id), int(request.session.get("userid"))) 
        else:
            bot_admin = False
    if not bot_admin:
        bot["api_token"] = None
    img_header_list = ["image/gif", "image/png", "image/jpeg", "image/jpg"]
    try:
        banner = bot["banner"].replace(" ", "%20").replace("\n", "")
    except:
        banner = ""
    bot_info = await get_bot(bot["bot_id"])
    
    promos = await get_promotions(bot["bot_id"])
    maint = await get_maint(bot["bot_id"])

    owners_lst = [(await get_user(obj["owner"])) for obj in owners if obj["owner"] is not None]
    print(owners_lst)
    owners_html = ""
    first_done = False
    last_done = False
    for i in range(0, len(owners_lst)):
        owner = owners_lst[i]
        if owner is None: 
            continue
        if last_done:
            owners_html += " and "
        elif first_done:
            owners_html += ", "
        owners_html += f"<a class='long-desc-link' href='/profile/{owner['id']}'>{owner['username']}</a>"
        if i >= len(owners_lst) - 2: # Twi to get last guy
            last_done = True
        else:
            first_done = True
    if bot["features"] is None:
        features = []
    else:
        features = bot["features"]
    
    bot_features = ", ".join([f"<a class='long-desc-link' href='/feature/{feature}'>{feature.replace('_', ' ').title()}</a>" for feature in features])
    if len(features) > 1:
        bot_features = replace_last(bot_features, ",", " and")
    if bot_info:
        bot = dict(bot)
        bot = bot | {"votes": human_format(bot["votes"]), "servers": human_format(bot["servers"]), "banner": banner.replace("\"", "").replace("'", "").replace("http://", "https://").replace("(", "").replace(")", "").replace("file://", ""), "shards": human_format(bot["shard_count"]), "owners_html": owners_html, "features": bot_features, "long_description": ldesc.replace("window.location", "").replace("document.ge", ""), "user": (await get_bot(bot_id))}
        #await db.execute("UPDATE bots SET username_cached = $2 WHERE bot_id = $1", int(bot_id), bot_info["username"])   
    else:
        return await templates.e(request, "Bot Not Found")
    _tags_fixed_bot = [tag for tag in tags_fixed if tag["id"] in bot["tags"]]
    form = await Form.from_formdata(request)
    bt.add_task(add_ws_event, bot_id, {"payload": "event", "id": str(uuid.uuid4()), "event": "view_bot", "context": {"user": request.session.get('userid'), "widget": widget}})
    if widget:
        f = "widget.html"
        reviews = [0, 1]
    else:
        f = "bot.html"
        reviews = await parse_reviews(bot_id)
    return await templates.TemplateResponse(f, {"request": request, "bot": bot, "bot_id": bot_id, "tags_fixed": _tags_fixed_bot, "form": form, "avatar": request.session.get("avatar"), "promos": promos, "maint": maint, "bot_admin": bot_admin, "review": review, "guild": main_server, "botp": True, "bot_reviews": reviews[0], "average_rating": reviews[1], "replace_last": replace_last})

#    id uuid primary key DEFAULT uuid_generate_v4(),
#   bot_id bigint not null,
#   star_rating float4 default 0.0,
#   review_text text,
#   review_upvotes integer default 0,
#   review_downvotes integer default 0,
#   flagged boolean default false,
#   epoch bigint

async def parse_bot_list(fetch: List[asyncpg.Record]) -> list:
    lst = []
    for bot in fetch:
        try:
            bot_info = await get_bot(bot["bot_id"])
            if bot_info is not None:
                bot = dict(bot)
                votes = bot["votes"]
                bot["bot_id"] = str(bot["bot_id"])
                servers = bot["servers"]
                del bot["votes"]
                del bot["servers"]
                banner = bot["banner"]
                del bot["banner"]
                if bot_info.get("avatar") is None:
                    bot_info["avatar"] = ""
                lst.append({"avatar": bot_info["avatar"].replace("?size=1024", "?size=128"), "username": bot_info["username"], "votes": human_format(votes), "servers": human_format(servers), "description": bot["description"], "banner": banner.replace("\"", "").replace("'", "").replace("http://", "https://").replace("(", "").replace(")", "").replace("file://", "")} | bot | bot_info)
        except:
            continue
    return lst

async def do_index_query(add_query: str, state: int = 0) -> List[asyncpg.Record]:
    base_query = f"SELECT description, banner, state, votes, servers, bot_id, invite, nsfw FROM bots WHERE state = {state}"
    end_query = "DESC LIMIT 12"
    return await db.fetch(" ".join((base_query, add_query, end_query)))

async def render_index(request: Request, api: bool):
    top_voted = await parse_bot_list((await do_index_query("ORDER BY votes")))
    new_bots = await parse_bot_list((await do_index_query("ORDER BY created_at"))) # and certified = true ORDER BY votes
    certified_bots = await parse_bot_list((await do_index_query("ORDER BY votes", state = 6))) # State 6 is certified
    base_json = {"tags_fixed": tags_fixed, "top_voted": top_voted, "new_bots": new_bots, "certified_bots": certified_bots, "roll_api": "/api/bots/random"}
    if not api:
        return await templates.TemplateResponse("index.html", {"request": request, "random": random} | base_json)
    else:
        return base_json

async def render_search(request: Request, q: str, api: bool):
    if q == "":
        if api:
            return abort(404)
        else:
            return RedirectResponse("/")
    bots = await db.fetch("SELECT DISTINCT bots.bot_id, bots.banner, bots.votes, bots.servers, bots.description, bots.invite, bots.nsfw FROM bots INNER JOIN bot_owner ON bots.bot_id = bot_owner.bot_id WHERE (bots.state = 0 OR bots.state = 6) and (bots.description ilike $1 OR bots.username_cached ilike $1 OR bot_owner.owner::text ilike $1) ORDER BY bots.votes LIMIT 6", f'%{q}%')
    search_bots = await parse_bot_list(bots)
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
        profiles = await db.fetch("SELECT DISTINCT users.user_id, users.description FROM users INNER JOIN bot_owner ON users.user_id = bot_owner.owner INNER JOIN bots ON bot_owner.bot_id = bots.bot_id WHERE ((bots.state = 0 OR bots.state = 6) AND (bots.username_cached ilike $1 OR bots.description ilike $1 OR bots.bot_id::text ilike $1)) OR (users.username ilike $1) AND users.deleted = false LIMIT 12", f'%{q}%')
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

# Check vanity of bot 
async def vanity_bot(vanity: str, compact = False):
    t = await db.fetchrow("SELECT type, redirect FROM vanity WHERE lower(vanity_url) = $1", vanity.lower())
    if t is None:
        return None
    if t["type"] == 1:
        type = "bot"
    else:
        type = "profile"
    if compact:
        return type, str(t["redirect"])
    return int(t["redirect"]), type

