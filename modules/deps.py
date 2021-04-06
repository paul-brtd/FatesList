from modules.imports import *

# FastAPI Limiter rl func
async def rl_key_func(request: Request) -> str:
    if request.headers.get("FatesList-RateLimitBypass") == ratelimit_bypass_key:
        return get_token(32)
    if "Authorization" in request.headers or "authorization" in request.headers:
        try:
            r = request.headers["Authorization"]
        except KeyError:
            r = request.headers["authorization"]
        check = await db.fetchrow("SELECT bot_id, certified FROM bots WHERE api_token = $1", r)
        if check is None:
            return ip_check(request)
        if check["certified"]:
            return get_token(32)
        return str(check["bot_id"])
    else:
        return ip_check(request)

async def _internal_user_fetch(userid: str, user_type: int) -> Optional[dict]:
    # Check if a suitable version is in the cache first before querying Discord

    CACHE_VER = 10 # Current cache ver

    if len(userid) not in [17, 18, 19, 20]: # Snowflake can be 17 - 21
        print("Ignoring blatantly wrong User ID")
        return None # This is impossible to actually exist on the discord API or on our cache

    # Query redis cache for some important info
    cache_redis = await redis_db.hget(str(userid), key = 'cache')
    if cache_redis is not None:
        cache = orjson.loads(cache_redis)
        if cache.get("fl_cache_ver") != CACHE_VER or cache.get("valid_user") is None or time.time() - cache['epoch'] > 60*60*8: # 8 Hour cacher
            # The cache is invalid, pass
            print("Not using cache for id ", userid)
            pass
        else:
            print("Using cache for id ", userid)
            fetch = False
            if cache.get("valid_user") and ((user_type == 2 and cache["bot"]) or user_type == 3):
                fetch = True
            elif cache.get("valid_user") and user_type == 1 and not cache["bot"]:
                fetch = True
            if fetch:
                return {"id": userid, "username": cache['username'], "avatar": cache['avatar'], "disc": cache["disc"], "status": cache["status"], "bot": cache["bot"]}
            return None

    # Add ourselves to cache
    valid_user = False
    bot = False
    username, avatar, disc = None, None, None # All are none at first

    try:
        print(f"Making API call to get user {userid}")
        bot_obj = await client.fetch_user(int(userid))
        valid_user = True
        bot = bot_obj.bot
    except Exception as ex:
        valid_user, bot = False, False
        print(ex)
        pass
    
    try:
        status = str(client.get_guild(main_server).get_member(int(userid)).status)
        print(status)
        if status == "online":
            status = 1
        elif status == "offline":
            status = 2
        elif status == "idle":
            status = 3
        elif status == "dnd":
            status = 4
        else:
            status = 0
    except Exception as ex:
        print(ex)
        status = 0

    if valid_user:
        username = bot_obj.name
        avatar = str(bot_obj.avatar_url)
        disc = bot_obj.discriminator
    else:
        username = ""
        avatar = ""
        disc = ""

    if bot and valid_user:
        print("Setting db username to " + username + " for " + str(userid))
        await db.execute("UPDATE bots SET username_cached = $2 WHERE bot_id = $1", int(userid), username)

    cache = orjson.dumps({"fl_cache_ver": CACHE_VER, "epoch": time.time(), "bot": bot, "username": username, "avatar": avatar, "disc": disc, "valid_user": valid_user, "status": status})
    await redis_db.hset(str(userid), key = "cache", value = cache)

    fetch = False
    if valid_user and ((user_type == 2 and bot) or user_type == 3):
        fetch = True
    elif user_type == 1 and valid_user and not bot:
        fetch = True
    if fetch:
        return {"id": userid, "username": username, "avatar": avatar, "disc": disc, "status": status, "bot": bot}
    return None

async def get_user(userid: int) -> Optional[dict]:
    return await _internal_user_fetch(str(int(userid)), 1)

async def get_bot(userid: int) -> Optional[dict]:
    return await _internal_user_fetch(str(int(userid)), 2)

async def get_any(userid: int) -> Optional[dict]:
    return await _internal_user_fetch(str(int(userid)), 3)

# Internal backend entry to check if one role is in staff and return a dict of that entry if so
@jit(forceobj=True)
def is_staff_internal(staff_json: dict, role: int) -> dict:
    for key in staff_json.keys():
        if int(role) == int(staff_json[key]["id"]):
            return staff_json[key]
    return None

@jit(forceobj=True)
def is_staff(staff_json: dict, roles: Union[list, int], base_perm: int) -> Union[bool, Optional[int]]:
    if type(roles) == list:
        max_perm = 0 # This is a cache of the max perm a user has
        for role in roles:
            if type(role) == discord.Role:
                role = role.id
            tmp = is_staff_internal(staff_json, role)
            if tmp is not None and tmp["perm"] > max_perm:
                max_perm = tmp["perm"]
        if max_perm >= base_perm:
            return True, max_perm
        return False, max_perm
    else:
        tmp = is_staff_internal(staff_json, roles)
        if tmp is not None and tmp["perm"] >= base_perm:
            return True, tmp["perm"]
        return False, tmp["perm"]
    return False, tmp["perm"]

async def add_maint(bot_id: int, type: int, reason: str):
    maints = await db.fetchrow("SELECT bot_id FROM bot_maint WHERE bot_id = $1", bot_id)
    if maints is None:
        return await db.execute("INSERT INTO bot_maint (bot_id, reason, type, epoch) VALUES ($1, $2, $3, $4)", bot_id, reason, type, time.time())
    return await db.execute("UPDATE bot_maint SET reason = $1, type = $2, epoch = $3 WHERE bot_id = $4", reason, type, time.time(), bot_id)

async def set_stats(*, bot_id: int, guild_count: int, shard_count: int, user_count: int, shards: int):
    if int(guild_count) > 300000000000 or int(shard_count) > 300000000000:
        return
    await db.execute("UPDATE bots SET servers = $1, shard_count = $2, user_count = $3, shards = $4 WHERE bot_id = $5", guild_count, shard_count, user_count, shards, bot_id)

async def add_promotion(bot_id: int, title: str, info: str, css: str, type: int):
    if css is not None:
        css = css.replace("</style", "").replace("<script", "")
    info = info.replace("</style", "").replace("<script", "")
    return await db.execute("INSERT INTO bot_promotions (bot_id, title, info, css, type) VALUES ($1, $2, $3, $4, $5)", bot_id, title, info, css, type)

async def add_event(bot_id: int, event: str, context: dict, *, send_event = True):
    if type(context) == dict:
        pass
    else:
        raise KeyError

    new_event_data = [event, str(time.time()), orjson.dumps(context).decode()]
    id = uuid.uuid4()
    apitok = await db.fetchrow("SELECT api_token FROM bots WHERE bot_id = $1", bot_id)
    if apitok is None:
        return
    asyncio.create_task(db.execute("INSERT INTO api_event (id, bot_id, events) VALUES ($1, $2, $3)", id, bot_id, new_event_data))
    webh = await db.fetchrow("SELECT webhook, webhook_type FROM bots WHERE bot_id = $1", int(bot_id))
    if webh is not None and webh["webhook"] not in ["", None] and webh["webhook_type"] is not None and send_event:
        uri = webh["webhook"]
        cont = True
        if webh["webhook_type"].upper() == "FC":
            f = requests.post
            json = {"event": event, "context": context, "bot_id": str(bot_id), "event_id": str(id)}
            headers = {"Authorization": apitok["api_token"]}
        elif webh["webhook_type"].upper() == "DISCORD" and event in "vote":
            webhook = DiscordWebhook(url=uri)
            user = await get_user(int(context["user_id"])) # Get the user
            bot = await get_bot(bot_id) # Get the bot
            embed = DiscordEmbed(
                title = "New Vote on Fates List",
                description=f"{user['username']} has just cast a vote for {bot['username']} on Fates List!\nIt now has {context['votes']} votes!\n\nThank you for supporting this bot\n**GG**",
                color=242424
            )
            webhook.add_embed(embed)
            response = webhook.execute()
            cont = False
        elif webh["webhook_type"].upper() == "VOTE" and event == "vote":
            f = requests.post
            json = {"id": str(context["user_id"]), "votes": context["votes"]}
            headers = {"Authorization": apitok["api_token"]}
        else:
            cont = False
        if cont:
            print(f"Method Given: {webh['webhook_type'].upper()}")
            print(f"JSON: {json}\nFunction: {f}\nURL: {uri}\nHeaders: {headers}")
            json = json | {"payload": "event", "mode": webh["webhook_type"].upper()}
            asyncio.create_task(f(uri, json = json, headers = headers))
    asyncio.create_task(add_ws_event(bot_id, {"payload": "event", "id": str(id), "event": event, "context": context}))
    return id

class Form(StarletteForm):
    pass

async def get_maint(bot_id: str) -> Union[bool, Optional[dict]]:
    api_data = await db.fetchrow("SELECT type, reason, epoch FROM bot_maint WHERE bot_id = $1", bot_id)
    if api_data is None:
        return {"type": 0, "reason": None, "epoch": None, "fail": True}
    api_data = dict(api_data)
    api_data["epoch"] = str(time.time())
    return api_data

async def is_bot_admin(bot_id: int, user_id: int):
    guild = client.get_guild(main_server)
    check = await db.fetchrow("SELECT owner, extra_owners FROM bots WHERE bot_id = $1", bot_id)
    if not check:
        return None
    try:
        user = guild.get_member(user_id)
    except:
        user = None
    if check["extra_owners"] is None:
        eo = []
    else:
        eo = check["extra_owners"]
    try:
        if check["owner"] == user_id or user_id in eo or (user is not None and is_staff(staff_roles, user.roles, 4)[0]):
            return True
        else:
            return False
    except:
        return False
async def get_promotions(bot_id: int) -> list:
    api_data = await db.fetch("SELECT id, title, info, css, type FROM bot_promotions WHERE bot_id = $1", bot_id)
    return api_data

async def get_user_token(uid: int, username: str) -> str:
    token = await db.fetchrow("SELECT username, api_token FROM users WHERE user_id = $1", int(uid))
    if token is None:
        flag = True
        while flag:
            token = get_token(101)
            tcheck = await db.fetchrow("SELECT api_token FROM users WHERE api_token = $1", token)
            if tcheck is None:
                flag = False
        await db.execute("INSERT INTO users (user_id, api_token, vote_epoch, username) VALUES ($1, $2, $3, $4)", int(uid), token, 0, username)
    else:
        # Update their username if needed
        if token["username"] != username:
            print("Updating profile")
            await db.execute("UPDATE users SET username = $1 WHERE user_id = $2", username, int(uid))
        token = token["api_token"]
        return token

async def get_bot_commands(bot_id: int) -> dict:
    cmd_raw = await db.fetch("SELECT id, slash, name, description, args, examples, premium_only, notes, doc_link FROM bot_commands WHERE bot_id = $1", bot_id)
    cmd = {cmd_raw_obj["id"]: dict(cmd_raw_obj) for cmd_raw_obj in cmd_raw}
    return cmd

#CREATE TABLE bot_stats_votes (
#   bot_id bigint,
#   total_votes bigint
#);

#CREATE TABLE bot_stats_votes_pm (
#   bot_id bigint,
#   epoch bigint,
#   votes bigint
#);

async def vote_bot(uid: int, bot_id: int, username, autovote: bool) -> Optional[list]:
    await get_user_token(uid, username) # Make sure we have a user profile first
    epoch = await db.fetchrow("SELECT vote_epoch FROM users WHERE user_id = $1", int(uid))
    if epoch is None:
        return [500]
    epoch = epoch["vote_epoch"]
    if autovote:
        WT = 60*60*11 # Autovote Wait Time
    else:
        WT = 60*60*8 # Wait Time
    if time.time() - epoch < WT:
        return [401, str(WT - (time.time() - epoch))]
    b = await db.fetchrow("SELECT webhook, votes FROM bots WHERE bot_id = $1", int(bot_id))
    voters = await db.fetchrow("SELECT timestamps FROM bot_voters WHERE bot_id = $1 AND user_id = $2", int(bot_id), int(uid))
    if b is None:
        return [404]
    if voters is None:
        await db.execute("INSERT INTO bot_voters (user_id, bot_id, timestamps) VALUES ($1, $2, $3)", int(uid), int(bot_id), [int(time.time())])
    else:
        voters["timestamps"].append(int(time.time()))
        ts = voters["timestamps"]
        await db.execute("UPDATE bot_voters SET timestamps = $1 WHERE bot_id = $2 AND user_id = $3", ts, int(bot_id), int(uid))
    await db.execute("UPDATE bots SET votes = votes + 1 WHERE bot_id = $1", int(bot_id))
    await db.execute("UPDATE users SET vote_epoch = $1 WHERE user_id = $2", time.time(), int(uid))

    # Update bot_stats
    check = await db.fetchrow("SELECT bot_id FROM bot_stats_votes WHERE bot_id = $1", int(bot_id))
    if check is None:
        await db.execute("INSERT INTO bot_stats_votes (bot_id, total_votes) VALUES ($1, $2)", int(bot_id), b["votes"] + 1)
    else:
        await db.execute("UPDATE bot_stats_votes SET total_votes = total_votes + 1 WHERE bot_id = $1", int(bot_id))

    event_id = asyncio.create_task(add_event(bot_id, "vote", {"username": username, "user_id": str(uid), "votes": b['votes'] + 1}))
    return []

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

@jit
def replace_last(string, delimiter, replacement):
    start, _, end = string.rpartition(delimiter)
    return start + replacement + end

# Get Bots Helper
async def render_bot(request: Request, bt: BackgroundTasks, bot_id: int, review: bool, widget: bool):
    guild = client.get_guild(main_server)
    print("Begin rendering bots")
    try:
        bot = dict(await db.fetchrow("SELECT js_whitelist, api_token, prefix, shard_count, queue, description, bot_library AS library, tags, banner, website, certified, votes, servers, bot_id, discord AS support, owner, extra_owners, banner, banned, disabled, github, features, invite_amount, css, html_long_description AS html_ld, long_description, donate, privacy_policy, nsfw FROM bots WHERE bot_id = $1", bot_id))
    except:
        return await templates.e(request, "Bot Not Found")
    print("Got here")
    if bot is None:
        return await templates.e(request, "Bot Not Found")
    if not bot["html_ld"]:
        ldesc = emd(markdown.markdown(bot['long_description'], extensions=["extra", "abbr", "attr_list", "def_list", "fenced_code", "footnotes", "tables", "admonition", "codehilite", "meta", "nl2br", "sane_lists", "toc", "wikilinks", "smarty", "md_in_html"]))
    else:
        ldesc = bot['long_description']
    # Take the h1...h5 anad drop it one lower
    ldesc = ldesc.replace("<h1", "<h2 style='text-align: center'").replace("<h2", "<h3").replace("<h4", "<h5").replace("<h6", "<p")

    if widget:
        extra_owners = []
        bot_admin = False
    else:
        if bot["extra_owners"] is None:
            eo = []
        else:
            eo = bot["extra_owners"]
        if "userid" in request.session.keys():
            bot_admin = await is_bot_admin(int(bot_id), int(request.session.get("userid"))) 
        else:
            bot_admin = False
    if not bot_admin:
        bot["api_token"] = None
    img_header_list = ["image/gif", "image/png", "image/jpeg", "image/jpg"]
    banner = bot["banner"].replace(" ", "%20").replace("\n", "")
    try:
        res = await requests.get(banner)
        if response.headers['Content-Type'] not in header_list:
            banner = "none"
    except:
        banner = "none"
    bot_info = await get_bot(bot["bot_id"])
    
    promos = await get_promotions(bot["bot_id"])
    maint = await get_maint(bot["bot_id"])

    extra_owners_lst = [(await get_user(id)) for id in eo]
    extra_owners = ""
    for eo in extra_owners_lst:
        if eo is None:
            continue
        extra_owners += f", <a class='long-desc-link' href='/profile/{eo['id']}'>{eo['username']}</a>"
    if len(extra_owners_lst) > 1:
        extra_owners = replace_last(extra_owners, ",", " and")
    
    if bot["features"] is None:
        features = []
    else:
        features = bot["features"]
    
    bot_features = ", ".join([f"<a class='long-desc-link' href='/feature/{feature}'>{feature.replace('_', ' ').title()}</a>" for feature in features])
    if len(features) > 1:
        bot_features = replace_last(bot_features, ",", " and")
    if bot_info:
        bot = dict(bot)
        bot = bot | {"votes": human_format(bot["votes"]), "servers": human_format(bot["servers"]), "banner": banner.replace("\"", "").replace("'", "").replace("http://", "https://").replace("(", "").replace(")", "").replace("file://", ""), "shards": human_format(bot["shard_count"]), "owner_pretty": await get_user(bot["owner"]), "extra_owners": extra_owners, "features": bot_features, "long_description": ldesc.replace("window.location", "").replace("document.ge", ""), "user": (await get_bot(bot_id))}
        #await db.execute("UPDATE bots SET username_cached = $2 WHERE bot_id = $1", int(bot_id), bot_info["username"])   
    else:
        return await templates.e(request, "Bot Not Found")
    _tags_fixed_bot = [tag for tag in tags_fixed if tag["id"] in bot["tags"]]
    form = await Form.from_formdata(request)
    bt.add_task(add_ws_event, bot_id, {"payload": "event", "id": str(uuid.uuid4()), "event": "view", "context": {"user": request.session.get('userid'), "widget": str(widget)}})
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

async def do_index_query(add_query: str) -> List[asyncpg.Record]:
    base_query = "SELECT description, banner, certified, votes, servers, bot_id, invite, nsfw FROM bots WHERE queue = false AND banned = false AND disabled = false"
    end_query = "DESC LIMIT 12"
    return await db.fetch(" ".join((base_query, add_query, end_query)))

async def render_index(request: Request, api: bool):
    top_voted = await parse_bot_list((await do_index_query("ORDER BY votes")))
    new_bots = await parse_bot_list((await do_index_query("ORDER BY created_at"))) # and certified = true ORDER BY votes
    certified_bots = await parse_bot_list((await do_index_query("and certified = true ORDER BY votes")))
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
    try:
        es = " OR owner = " + str(int(q)) + f" OR {str(q)} = ANY(extra_owners) OR bot_id = " + str(int(q))
    except:
        es = ""
    desc = ("SELECT bot_id FROM bots WHERE (queue = false and banned = false and disabled = false) and (description ilike '%" + re.sub(r'\W+|_', ' ', q) + "%'" + es + ")")
    print(desc)
    desc = await db.fetch(desc)
    userc = await db.fetch("SELECT bot_id FROM bots WHERE username_cached ilike '%" + re.sub(r'\W+|_', ' ', q) + "%'")
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
        abc = ("SELECT description, banner, certified, votes, servers, bot_id, invite, nsfw FROM bots WHERE queue = false and banned = false and disabled = false and bot_id IN (" + data + ") ORDER BY votes DESC LIMIT 12")
        fetch = await db.fetch(abc)
    search_bots = await parse_bot_list(fetch)
    if not api:
        return await templates.TemplateResponse("search.html", {"request": request, "search_bots": search_bots, "tags_fixed": tags_fixed, "query": q, "profile_search": False})
    else:
        return {"search_bots": search_bots, "tags_fixed": tags_fixed, "query": q, "profile_search": False}

async def render_profile_search(request: Request, q: str, api: bool):
    if q is None:
        query = ""
    else:
        query = q
    try:
        es = " OR user_id = " + str(int(query))
    except:
        es = ""
    if query.replace(" ", "") != "":
        profiles = "SELECT user_id, description, certified FROM users" # Base profile
        if query != "":
            profiles = profiles + (" WHERE (username ilike '%" + re.sub(r'\W+|_', ' ', query) + "%'" + es + ")")
        profiles = await db.fetch(profiles + " LIMIT 12")
    else:
        profiles = []
    profile_obj = []
    for profile in profiles:
        profile_info = await get_user(profile["user_id"])
        if profile_info:
            profile_obj.append({"banner": None, "description": profile["description"], "certified": profile["certified"] == True} | profile_info)
    if not api:
        return await templates.TemplateResponse("search.html", {"request": request, "tags_fixed": tags_fixed, "profile_search": True, "query": query, "profiles": profile_obj})
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

# WebSocket Base Code

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.fl_loaded = False

    async def connect(self, websocket: WebSocket, api: bool = True):
        await websocket.accept()
        if api:
            try:
                print(websocket.api_token)
            except:
                websocket.api_token = []
                websocket.bot_id = []
                websocket.authorized = False
        else:
            websocket.api_token = []
            websocket.bot_id = []
            websocket.authorized = False
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        try:
            await websocket.close(code=4005)
        except:
            pass
        self.active_connections.remove(websocket)

        # Delete stale websocket credentials
        websocket.api_token = []
        websocket.bot_id = [] # 
        websocket.authorized = False

    async def send_personal_message(self, message, websocket: WebSocket):
        i = 0
        if websocket not in self.active_connections:
            await manager.disconnect(websocket)
            return False
        while i < 6: # Try to send message 5 times
            try:
                await websocket.send_json(message)
                i = 6
            except:
                if i == 5:
                    await manager.disconnect(websocket)
                    return False
                else:
                    i+=1

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_json(message)

async def ws_close(websocket: WebSocket, code: int):
    try:
        return await websocket.close(code=code)
    except:
        return

builtins.manager = ConnectionManager()
builtins.manager_chat = ConnectionManager()

async def get_events(api_token: Optional[str] = None, bot_id: Optional[str] = None, event_id: Optional[uuid.UUID] = None):
    if api_token is None and bot_id is None:
        return {"events": []}
    if api_token is None:
        bid = await db.fetchrow("SELECT bot_id, servers FROM bots WHERE bot_id = $1", bot_id)
    else:
        bid = await db.fetchrow("SELECT bot_id, servers FROM bots WHERE api_token = $1", api_token)
    if bid is None:
        return {"events": []}
    uid = bid["bot_id"]
    # As a replacement/addition to webhooks, we have API events as well to allow you to quickly get old and new events with their epoch
    if event_id is not None:
        api_data = await db.fetchrow("SELECT id, events FROM api_event WHERE bot_id = $1 AND id = $2", uid, event_id)
        if api_data is None:
            return {"events": []}
        event = api_data["events"]
        return {"events": [{"id": uid,  "event": event[0], "epoch": event[1], "context": event[2]}]}

    api_data = await db.fetch("SELECT id, events FROM api_event WHERE bot_id = $1 ORDER BY id", uid)
    if api_data == []:
        return {"events": []}
    events = []
    for _event in api_data:
        event = _event["events"]
        uid = _event["id"]
        events.append({"id": uid,  "event": event[0], "epoch": event[1], "context": orjson.loads(event[2])})
    ret = {"events": events}
    return ret

class templates():
    @staticmethod
    async def TemplateResponse(f, arg_dict, not_error = True):
        guild = client.get_guild(main_server)
        try:
            request = arg_dict["request"]
        except:
            raise KeyError
        status = arg_dict.get("status_code")
        if "userid" in request.session.keys():
            arg_dict["css"] = request.session.get("user_css")
            try:
                user = guild.get_member(int(request.session["userid"]))
            except:
                user = None
            banned = await db.fetchval("SELECT banned FROM users WHERE user_id = $1", int(request.session["userid"]))
            if banned == 1 and not_error:
                ban_type = "global"
                return await templates.e(request, f"You have been {ban_type} banned from Fates List<br/>", status_code = 403)
            if user is not None:
                request.session["staff"] = is_staff(staff_roles, user.roles, 2)
            else:
                pass
            arg_dict["staff"] = request.session.get("staff", [False])
            arg_dict["avatar"] = request.session.get("avatar")
            arg_dict["username"] = request.session.get("username")
            arg_dict["userid"] = int(request.session.get("userid"))
            arg_dict["user_token"] = request.session.get("user_token")
            try:
                arg_dict["access_token"] = orjson.dumps(request.session.get("access_token")).decode("utf-8")
            except:
                pass
            arg_dict["scopes"] = request.session.get("dscopes_str")
        else:
            arg_dict["staff"] = [False]
        print(arg_dict["staff"])
        arg_dict["site_url"] = site_url
        arg_dict["form"] = await Form.from_formdata(request)
        arg_dict["data"] = arg_dict.get("data")
        if status is None:
            return _templates.TemplateResponse(f, arg_dict)
        return _templates.TemplateResponse(f, arg_dict, status_code = status)

    @staticmethod
    async def error(f, arg_dict, status_code):
        arg_dict["status_code"] = status_code
        return await templates.TemplateResponse(f, arg_dict, not_error = False)

    @staticmethod
    async def e(request, reason: str, status_code: int = 404, *, main: Optional[str] = ""):
        return await templates.error("message.html", {"request": request, "message": main, "context": reason, "retmain": True}, status_code)

@jit(forceobj=True)
def url_startswith(url, begin, slash = True):
    # Slash indicates whether to check /route or /route/
    if slash:
       begin = begin + "/"
    return str(url).startswith(site_url + begin)

_templates = Jinja2Templates(directory="templates")

@jit(forceobj=True)
def etrace(ex):
    trace = []
    tb = ex.__traceback__
    while tb is not None:
        trace.append({
            "filename": tb.tb_frame.f_code.co_filename,
            "name": tb.tb_frame.f_code.co_name,
            "lineno": tb.tb_lineno
        })
        tb = tb.tb_next
    return str({
        'type': type(ex).__name__,
        'message': str(ex),
        'trace': trace
    })


class FLError():
    @staticmethod
    async def log(request, exc, error_id, curr_time):
        site_errors = client.get_channel(site_errors_channel)
        traceback = exc.__traceback__
        try:
            fl_info = f"Error ID: {error_id}\n\nMinimal output\n\n"
            while traceback is not None:
                fl_info += f"{traceback.tb_frame.f_code.co_filename}: {traceback.tb_lineno}\n"
                traceback = traceback.tb_next
            try:
                fl_info += f"\n\nExtended output\n\n{etrace(exc)}"
            except:
                fl_info += f"\n\nExtended output\n\nNo extended output could be logged..."
        except:
            pass
        await site_errors.send(f"500 (Internal Server Error) at {str(request.url).replace('https://', '')}\n\n**Error**: {exc}\n**Type**: {type(exc)}\n**Data**: File will be uploaded below if we didn't run into errors collecting logging information\n\n**Error ID**: {error_id}\n**Time When Error Happened**: {curr_time}")
        fl_file = discord.File(io.BytesIO(bytes(fl_info, 'utf-8')), f'{error_id}.txt')
        if fl_file is not None:
            await site_errors.send(file=fl_file)
        else:
            await site_errors.send("No extra information could be logged and/or send right now")

    @staticmethod
    async def error_handler(request, exc):
        error_id = str(uuid.uuid4())
        curr_time = str(datetime.datetime.now())
        try:
            status_code = exc.status_code # Check for 500 using status code presence
        except:
            if type(exc) == RequestValidationError:
                exc.status_code = 422
            else:
                exc.status_code = 500
        match exc.status_code:
            case 500:
                asyncio.create_task(FLError.log(request, exc, error_id, curr_time))
                return HTMLResponse(f"<strong>500 Internal Server Error</strong><br/>Fates List had a slight issue and our developers and looking into what happened<br/><br/>Error ID: {error_id}<br/>Time When Error Happened: {curr_time}", status_code=500)
            case 404:
                if url_startswith(request.url, "/bot"):
                    msg = "Bot Not Found"
                    code = 404
                elif url_startswith(request.url, "/profile"):
                    msg = "Profile Not Found"
                    code = 404
                else:
                    msg = "404\nNot Found"
                    code = 404
            case 401:
                msg = "401\nNot Authorized"
                code = 401
            case 422:
                if url_startswith(request.url, "/bot"):
                    msg = "Bot Not Found"
                    code = 404
                elif url_startswith(request.url, "/profile"):
                    msg = "Profile Not Found"
                    code = 404
                else:
                    msg = "Invalid Data Provided<br/>" + str(exc)
                    code = 422
            case _:
                msg = "Unknown Error"
                code = 400

        json = url_startswith(request.url, "/api")
        if json:
            if exc.status_code != 422:
                return await http_exception_handler(request, exc)
            else:
                return await request_validation_exception_handler(request, exc)
        return await templates.e(request, msg, code)

async def add_ws_event(bot_id: int, ws_event: dict) -> None:
    """A WS Event must have the following format:
        - {id: Event ID, event: Event Name, context: Context, type: Event Type}
    """
    curr_ws_events = await redis_db.hget(str(bot_id), key = "ws")
    if curr_ws_events is None:
        curr_ws_events = {}
    else:
        curr_ws_events = orjson.loads(curr_ws_events)
    id = ws_event["id"]
    del ws_event["id"]
    curr_ws_events[id] = ws_event
    await redis_db.hset(str(bot_id), key = "ws", value = orjson.dumps(curr_ws_events)) # Add it to curr_ws_events
    await redis_db.publish(str(bot_id), orjson.dumps({id: ws_event})) # Publish it to ws_events

class BotActions():
    def __init__(self, bot):
        self.__dict__.update(bot) # Add all kwargs to function
        print(bot) # DEBUG
        if "bt" not in self.__dict__ or "user_id" not in self.__dict__:
            raise SyntaxError("Background Task and User ID must be in dict")

    async def base_check(self) -> Optional[str]:
        """Perform basic checks for adding/editting bots"""
        if self.bot_id == "" or self.prefix == "" or self.invite == "" or self.description == "" or self.long_description == "" or len(self.prefix) > 9:
            return "Please ensure you have filled out all the required fields and that your prefix is less than 9 characters."

        if self.tags == "":
            return "You must select tags for your bot"

        if not self.banner.startswith("https://") and self.banner not in ["", "none"]:
            return "Your banner does not use https://. Please change it"
        
        if not self.invite.startswith("https://discord.com") or "oauth" not in self.invite:
            return "Invalid Bot Invite: Your bot invite must be in the format of https://discord.com/api/oauth2... or https://discord.com/oauth2..."

        if len(self.description) > 110:
            return "Your short description must be shorter than 110 characters"

        try:
            bot_object = await get_bot(self.bot_id)
        except:
            return "According to Discord's API and our cache, your bot does not exist. Please try again after 2 hours."

        if not bot_object:
            return "According to Discord's API and our cache, your bot does not exist. Please try again after 2 hours."
        
        if type(self.tags) != list:
            self.tags = self.tags.split(",")
        
        flag = False
        for test in self.tags:
            if test not in TAGS:
                return "One of your tags doesn't exist internally. Please check your tags again"
            flag = True

        if not flag:
            return "You must select tags for your bot"

        if self.banner != "none" and self.banner != "":
            img = await requests.get(self.banner)
            if img.headers.get("Content-Type") is None or img.headers.get("Content-Type").split("/")[0] != "image":
                return "Banner URL is not an image. Please make sure it is setting the proper Content-Type"

        if self.donate != "" and not (self.donate.startswith("https://patreon.com") or self.donate.startswith("https://paypal.me")):
            return "Only Patreon and Paypal.me are allowed for donation links as of right now."

        if self.extra_owners == "":
            self.extra_owners = []
        else:
            if type(self.extra_owners) != list:
                self.extra_owners = self.extra_owners.split(",")

        try:
            self.extra_owners = [int(id.replace(" ", "")) for id in self.extra_owners]
        except:
            return "One of your extra owners doesn't exist or you haven't comma-seperated them."

        if self.github != "" and not self.github.startswith("https://www.github.com"):
            return "Your github link must start with https://www.github.com"

        self.privacy_policy = self.privacy_policy.replace("http://", "https://")
        if self.privacy_policy != "" and not self.privacy_policy.startswith("https://"):
            return "Your privacy policy must be a proper URL starting with https://. URLs which start with http:// will be automatically converted to HTTPS"

        if self.vanity == "":
            pass
        else:
            vanity_check = await db.fetchrow("SELECT DISTINCT vanity_url FROM vanity WHERE lower(vanity_url) = $1 AND redirect != $2", self.vanity.replace(" ", "").lower(), self.bot_id)
            if vanity_check is not None or self.vanity.replace("", "").lower() in ["bot", "docs", "redoc", "doc", "profile", "server", "bots", "servers", "search", "invite", "discord", "login", "logout", "register", "admin"] or self.vanity.replace("", "").lower().__contains__("/"):
                return "Your custom vanity URL is already in use or is reserved"

        return None # None means success

    async def edit_check(self):
        """Perform extended checks for editting bots"""
        check = await self.base_check() # Initial base checks
        if check is not None:
            return check

        check = await is_bot_admin(int(self.bot_id), int(self.user_id)) # Check for owner
        if check is None:
            return "This bot doesn't exist in our database."
        elif check is False:
            return "You aren't the owner of this bot."

        check = await get_user(self.user_id)
        if check is None:
            return "You do not exist on the Discord API. Please wait for a few hours and try again"

        return None # None means success

    async def add_check(self):
        """Perform extended checks for adding bots"""
        check = await self.base_check() # Initial base checks
        if check is not None:
            return check

        if (await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1", self.bot_id)) is not None:
            return "This bot already exists on Fates List"

        return None # None means success

    async def add_bot(self):
        """Add a bot"""
        check = await self.add_check() # Perform add bot checks
        if check is not None:
            return check

        creation = time.time()

        self.bt.add_task(self.add_bot_bt, int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.tags, self.extra_owners, creation, self.invite, self.features, self.html_long_description, self.css, self.donate, self.github, self.webhook, self.webhook_type, self.vanity, self.privacy_policy, self.nsfw)
        return None # None means success

    async def edit_bot(self):
        """Edit a bot"""
        check = await self.edit_check() # Perform edit bot checks
        if check is not None:
            return check

        creation = time.time()
        self.bt.add_task(self.edit_bot_bt, int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.tags, self.extra_owners, creation, self.invite, self.webhook, self.vanity, self.github, self.features, self.html_long_description, self.webhook_type, self.css, self.donate, self.privacy_policy, self.nsfw)

    @staticmethod
    async def add_bot_bt(user_id, bot_id, prefix, library, website, banner, support, long_description, description, tags, extra_owners, creation, invite, features, html_long_description, css, donate, github, webhook, webhook_type, vanity, privacy_policy, nsfw):
        await db.execute("""INSERT INTO bots (
                bot_id, prefix, bot_library,
                invite, website, banner, 
                discord, long_description, description,
                tags, owner, extra_owners,
                votes, servers, shard_count,
                created_at, api_token, features, 
                html_long_description, css, donate,
                github, webhook, webhook_type, 
                privacy_policy, nsfw) VALUES(
                $1, $2, $3,
                $4, $5, $6,
                $7, $8, $9,
                $10, $11, $12,
                $13, $14, $15,
                $16, $17, $18,
                $19, $20, $21,
                $22, $23, $24, 
                $25, $26)""", bot_id, prefix, library, invite, website, banner, support, long_description, description, tags, user_id, extra_owners, 0, 0, 0, int(creation), get_token(132), features, html_long_description, css, donate, github, webhook, webhook_type, privacy_policy, nsfw)
        if vanity.replace(" ", "") != '':
            await db.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 1, vanity, bot_id)

        await add_event(bot_id, "add_bot", {})
        owner = int(user_id)
        channel = client.get_channel(bot_logs)
        bot_name = (await get_bot(bot_id))["username"]
        add_embed = discord.Embed(title="New Bot!", description=f"<@{owner}> added the bot <@{bot_id}>({bot_name}) to queue!", color=0x00ff00)
        add_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{bot_id}")
        try:
            member = channel.guild.get_member(owner)
            if member is not None:
                await member.send(embed = add_embed)
        except:
            pass
        await channel.send(f"<@&{staff_ping_add_role}>", embed = add_embed)

    @staticmethod
    async def edit_bot_bt(user_id, bot_id, prefix, library, website, banner, support, long_description, description, tags, extra_owners, creation, invite, webhook, vanity, github, features, html_long_description, webhook_type, css, donate, privacy_policy, nsfw):
        await db.execute("UPDATE bots SET bot_library=$2, webhook=$3, description=$4, long_description=$5, prefix=$6, website=$7, discord=$8, tags=$9, banner=$10, invite=$11, extra_owners = $12, github = $13, features = $14, html_long_description = $15, webhook_type = $16, css = $17, donate = $18, privacy_policy = $19, nsfw = $20 WHERE bot_id = $1", bot_id, library, webhook, description, long_description, prefix, website, support, tags, banner, invite, extra_owners, github, features, html_long_description, webhook_type, css, donate, privacy_policy, nsfw)
        check = await db.fetchrow("SELECT vanity FROM vanity WHERE redirect = $1", bot_id)
        if check is None:
            print("am here")
            if vanity.replace(" ", "") != '':
                await db.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 1, vanity, bot_id)
        else:
            if vanity == '':
                vanity = None

            await db.execute("UPDATE vanity SET vanity_url = $1 WHERE redirect = $2", vanity, bot_id)
        await add_event(bot_id, "edit_bot", {"user": str(user_id)})
        channel = client.get_channel(bot_logs)
        owner = int(user_id)
        edit_embed = discord.Embed(title="Bot Edit!", description=f"<@{owner}> has edited the bot <@{bot_id}>!", color=0x00ff00)
        edit_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{bot_id}")
        await channel.send(embed = edit_embed)

async def bot_auth(bot_id: int, api_token: str, *, fields: Optional[str] = None):
    if fields is None:
        return await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(api_token))
    return await db.fetchrow(f"SELECT bot_id, {fields} FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(api_token))

async def user_auth(user_id: int, api_token: str, fields: Optional[str] = None):
    if fields is None:
        return await db.fetchval("SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", user_id, str(api_token))
    return await db.fetchrow(f"SELECT user_id, {fields} FROM users WHERE user_id = $1 AND api_token = $2", user_id, str(api_token))

