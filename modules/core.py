from modules.imports import *

# FastAPI Limiter rl func
async def rl_key_func(request: Request) -> str:
    if request.headers.get("FatesList-RateLimitBypass") == ratelimit_bypass_key: # Check ratelimit key
        return get_token(32) # Disable
    if "Authorization" in request.headers or "authorization" in request.headers:
        try: # Check for auth header
            r = request.headers["Authorization"]
        except KeyError:
            r = request.headers["authorization"]
        check = await db.fetchrow("SELECT bot_id, certified FROM bots WHERE api_token = $1", r) # Check api token
        if check is None:
            return ip_check(request) # Invalid api token, fallback to ip
        if check["certified"]:
            return get_token(32) # Disable since certified bots are exempt
        return str(check["bot_id"]) # Otherwise, ratelimit using bot id
    else:
        return ip_check(request) # Fallback to ip

async def _internal_user_fetch(userid: str, user_type: int) -> Optional[dict]:
    # Check if a suitable version is in the cache first before querying Discord

    CACHE_VER = 10 # Current cache ver

    if len(userid) not in [17, 18, 19, 20]: # Snowflake can be 17 - 21
        print("Ignoring blatantly wrong User ID")
        return None # This is impossible to actually exist on the discord API or on our cache

    # Query redis cache for some important info
    cache_redis = await redis_db.hget(str(userid), key = 'cache') # This is bot in cache
    if cache_redis is not None: # We got a match
        cache = orjson.loads(cache_redis) # Make it JSON
        cache_time = time.time() - cache['epoch']
        if cache.get("fl_cache_ver") != CACHE_VER or (cache.get("valid_user") is None and time.time() - cache_time > 60*10) or cache_time > 60*60*8: # Check for cache expiry of 8 hours for proper user, 10 minutes for invalid, proper cache version and that its a valid user
            # The cache is invalid, pass and make discord api call
            print("Not using cache for id ", userid)
            pass
        else:
            print("Using cache for id ", userid) # Use cache
            fetch = False
            if cache.get("valid_user") and ((user_type == 2 and cache["bot"]) or user_type == 3): # Valid user and bot where bot is requested or all users requested
                fetch = True
            elif cache.get("valid_user") and user_type == 1 and not cache["bot"]: # Valid users and user where user is requested or all users requested
                fetch = True
            if fetch: # We got a match
                return {"id": userid, "username": cache['username'], "avatar": cache['avatar'], "disc": cache["disc"], "status": cache["status"], "bot": cache["bot"]}
            return None # We got a bot, but not fitting in constraints

    # Add ourselves to cache
    valid_user = False # Flag for valid user
    bot = False # Flag for bot
    username, avatar, disc = None, None, None # All are none at first

    try:
        print(f"Making API call to get user {userid}")
        bot_obj = await client.fetch_user(int(userid)) # Use fetch user to actually use HTTP api and not cache to allow bots not in guild
        valid_user = True # It worked and didn't error, set valid_user
        bot = bot_obj.bot # Set bot flag accordingly
    except Exception as ex:
        valid_user, bot = False, False # Not a proper got, cache to avoid repitition
        print(ex)

    try:
        status = str(client.get_guild(main_server).get_member(int(userid)).status) # Get the status by getting guild, getting member and then setting status, may fail if not in guild so catch that using try except above
        print(status)
        if status == "online":
            status = 1 # Online
        elif status == "offline":
            status = 2 # Offline
        elif status == "idle":
            status = 3 # Idle
        elif status == "dnd":
            status = 4 # Do Not Disturb
        else:
            status = 0 # Fallback status
    except Exception as ex:
        print(ex)
        status = 0 # Fallback status

    if valid_user: # Get username, avatar and disc
        username = bot_obj.name
        avatar = str(bot_obj.avatar_url)
        disc = bot_obj.discriminator
    else:
        username = ""
        avatar = ""
        disc = ""

    if bot and valid_user: # Update cached username in postgres if valid username in asyncio background task
        print("Setting db username to " + username + " for " + str(userid))
        asyncio.create_task(db.execute("UPDATE bots SET username_cached = $2 WHERE bot_id = $1", int(userid), username))

    cache = orjson.dumps({"fl_cache_ver": CACHE_VER, "epoch": time.time(), "bot": bot, "username": username, "avatar": avatar, "disc": disc, "valid_user": valid_user, "status": status}) # Create cache and dump it to string for caching
    await redis_db.hset(str(userid), key = "cache", value = cache) # Add/Update redis

    fetch = False
    if valid_user and ((user_type == 2 and bot) or user_type == 3): # Same as when cached, see that for this
        fetch = True
    elif user_type == 1 and valid_user and not bot:
        fetch = True
    if fetch:
        return {"id": userid, "username": username, "avatar": avatar, "disc": disc, "status": status, "bot": bot}
    return None

async def get_user(userid: int) -> Optional[dict]:
    return await _internal_user_fetch(str(int(userid)), 1) # 1 means user

async def get_bot(userid: int) -> Optional[dict]:
    return await _internal_user_fetch(str(int(userid)), 2) # 2 means bot

async def get_any(userid: int) -> Optional[dict]:
    return await _internal_user_fetch(str(int(userid)), 3) # 3 means all

class Serializer(object):
    @staticmethod
    def serialize(object):
        return orjson.dumps(object, default=lambda o: o.__dict__.values()[0]).decode("utr-8")

class StaffMember(BaseModel, Serializer):
    """Represents a staff member in Fates List""" 
    name: str
    id: int
    perm: int

# Internal backend entry to check if one role is in staff and return a dict of that entry if so
@jit(forceobj=True)
def _get_staff_member(staff_json: dict, role: int) -> StaffMember:
    for key in staff_json.keys(): # Loop through all keys in staff json
        if int(role) == int(staff_json[key]["id"]): # Check if role matches
            return StaffMember(name = key, id = staff_json[key]["id"], perm = staff_json[key]["perm"]) # Return the staff json role data
    return StaffMember(name = "user", id = staff_json["user"]["id"], perm = 1) # Fallback to perm 1 user member

@jit(forceobj = True)
def is_staff(staff_json: dict, roles: Union[list, int], base_perm: int) -> Union[bool, int, StaffMember]:
    if type(roles) != list and type(roles) != tuple:
        roles = [roles]
    max_perm = 0 # This is a cache of the max perm a user has
    sm = StaffMember(name = "user", id = staff_json["user"]["id"], perm = 1) # Initially
    bak_sm = sm # Backup staff member
    for role in roles: # Loop through all roles
        if type(role) == discord.Role:
            role = role.id
        sm = _get_staff_member(staff_json, role)
        if sm.perm > max_perm:
            max_perm = sm.perm
            bak_sm = sm # Back it up so it doesnt get overwritten
    if max_perm >= base_perm:
        return True, max_perm, bak_sm # Use backup and not overwritten one
    return False, max_perm, sm # Use normal one

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
        raise TypeError("Event must be a dict")

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
    check = await db.fetch("SELECT owner FROM bot_owner WHERE bot_id = $1", bot_id)
    if not check:
        return None
    owner_lst = [obj["owner"] for obj in check]
    try:
        user = guild.get_member(user_id)
    except:
        user = None
    try:
        if user_id in owner_lst or (user is not None and is_staff(staff_roles, user.roles, 4)[0]):
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
    try:
        bot = dict(await db.fetchrow("SELECT js_whitelist, api_token, prefix, shard_count, state, description, bot_library AS library, tags, banner, website, certified, votes, servers, bot_id, discord AS support, banner, disabled, github, features, invite_amount, css, html_long_description AS html_ld, long_description, donate, privacy_policy, nsfw FROM bots WHERE bot_id = $1", bot_id))
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
    base_query = "SELECT description, banner, certified, votes, servers, bot_id, invite, nsfw FROM bots WHERE state = 0"
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
    desc_query = ("SELECT bot_id FROM bots WHERE (state = 0 and banned = false and disabled = false) and (description ilike '%" + re.sub(r'\W+|_', ' ', q) + "%')")
    ownerc = await db.fetch("SELECT bot_id FROM bot_owner WHERE owner::text ilike '%" + re.sub(r'\W+|_', ' ', q) + "%'")
    desc = await db.fetch(desc_query)
    desc = list(set([id["bot_id"] for id in desc]).union(set([id["bot_id"] for id in ownerc])))
    userc = await db.fetch("SELECT bot_id FROM bots WHERE username_cached ilike '%" + re.sub(r'\W+|_', ' ', q) + "%'")
    bids = list(set(desc).union(set([id["bot_id"] for id in userc])))
    data = str(tuple([int(bid) for bid in bids])).replace("(", "").replace(")", "")
    if data.replace(" ", "") in ["()", None, ",", ""]:
        fetch = []
    elif data.split(",")[-1].replace(" ", "") == "":
        data = data.replace(",", "")
        fetch = None
    else:
        fetch = None
    if fetch is None:
        abc = ("SELECT description, banner, certified, votes, servers, bot_id, invite, nsfw FROM bots WHERE state = 0 and banned = false and disabled = false and bot_id IN (" + data + ") ORDER BY votes DESC LIMIT 12")
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
                staff = is_staff(staff_roles, user.roles, 2)
                request.session["staff"] = staff[0], staff[1], staff[2].dict()
            else:
                pass
            arg_dict["staff"] = request.session.get("staff")
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
        arg_dict["site_url"] = site_url
        arg_dict["form"] = await Form.from_formdata(request)
        arg_dict["data"] = arg_dict.get("data")
        arg_dict["path"] = request.url.path
        arg_dict["enums"] = enums
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
        traceback = exc.__traceback__ # Get traceback from exception
        site_errors = client.get_channel(site_errors_channel) # Get site errors channel
        if site_errors is None: # If this is None, config is wrong or we arent connected to Discord yet, in this case, raise traceback
            raise traceback
        try:
            fl_info = f"Error ID: {error_id}\n\nMinimal output\n\n" # Initial header
            while traceback is not None: # Loop through traceback recursively
                fl_info += f"{traceback.tb_frame.f_code.co_filename}: {traceback.tb_lineno}\n" # tb_frame.f_code.co_filename is the filename and tb_lineno is line number
                traceback = traceback.tb_next # Get the next part of traceback 
            try:
                fl_info += f"\n\nExtended output\n\n{etrace(exc)}" # Extended output
            except:
                fl_info += f"\n\nExtended output\n\nNo extended output could be logged..." # Could not log anything
        except:
            pass
        await site_errors.send(f"500 (Internal Server Error) at {str(request.url).replace('https://', '')}\n\n**Error**: {exc}\n**Type**: {type(exc)}\n**Data**: File will be uploaded below if we didn't run into errors collecting logging information\n\n**Error ID**: {error_id}\n**Time When Error Happened**: {curr_time}") # Send the 500 message to site errors
        fl_file = discord.File(io.BytesIO(bytes(fl_info, 'utf-8')), f'{error_id}.txt') # Create a file on discord
        if fl_file is not None:
            await site_errors.send(file=fl_file) # Send it
        else:
            await site_errors.send("No extra information could be logged and/or send right now") # Could not send it

    @staticmethod
    async def error_handler(request, exc):
        error_id = str(uuid.uuid4()) # Create a error id
        curr_time = str(datetime.datetime.now()) # Get time error happened
        try:
            status_code = exc.status_code # Check for 422 and 500 using status code presence
        except: # 500 and 422 do not have status code
            if type(exc) == RequestValidationError: # This is when incorrect arguments were passed (422)
                exc.status_code = 422
            else: # Internal Server Error (500)
                exc.status_code = 500
        match exc.status_code: # Python 3.10 introduced pattern matching, use that to check for http code
            case 500:
                asyncio.create_task(FLError.log(request, exc, error_id, curr_time)) # Try and log what happened
                return HTMLResponse(f"<strong>500 Internal Server Error</strong><br/>Fates List had a slight issue and our developers and looking into what happened<br/><br/>Error ID: {error_id}<br/>Time When Error Happened: {curr_time}\nPlease check our support server at <a href='{support_url}'>{support_url}</a> for more information", status_code=500) # Send 500 error to user with aupport server
            case 404: 
                if url_startswith(request.url, "/bot"): # Bot 404
                    msg = "Bot Not Found"
                    code = 404
                elif url_startswith(request.url, "/profile"): # Profile 404
                    msg = "Profile Not Found"
                    code = 404
                else: # Regular 404
                    msg = "404\nNot Found"
                    code = 404
            case 401:
                msg = "401\nNot Authorized"
                code = 401
            case 403:
                msg = "401\nForbidden"
                code = 403
            case 422:
                if url_startswith(request.url, "/bot"): # Bot 422 which is actually 404 to us
                    msg = "Bot Not Found"
                    code = 404
                elif url_startswith(request.url, "/profile"): # Profile 422 which is actually 404 to us
                    msg = "Profile Not Found"
                    code = 404
                else:
                    msg = "Invalid Data Provided<br/>" + str(exc) # Regular 422
                    code = 422
            case _:
                msg = "Unknown Error" # Unknown error, no case for it yet
                code = 400

        json = url_startswith(request.url, "/api") # Check if api route, return JSON if it is
        if json: # If api route, return JSON
            if exc.status_code != 422:
                return await http_exception_handler(request, exc) # 422 needs special request handler, all others can use this
            else:
                return await request_validation_exception_handler(request, exc) # Other codes can use normal one, 422 needs this
        return await templates.e(request, msg, code) # Otherwise return error

async def add_ws_event(bot_id: int, ws_event: dict) -> None:
    """A WS Event must have the following format:
        - {id: Event ID, event: Event Name, context: Context, type: Event Type}
    """
    curr_ws_events = await redis_db.hget(str(bot_id), key = "ws") # Get all the websocket events from the ws key
    if curr_ws_events is None:
        curr_ws_events = {} # No ws events means empty dict
    else:
        curr_ws_events = orjson.loads(curr_ws_events) # Otherwise, orjson load the current events
    id = ws_event["id"] # Get id
    del ws_event["id"] # Remove id
    curr_ws_events[id] = ws_event # Add event to current ws events
    await redis_db.hset(str(bot_id), key = "ws", value = orjson.dumps(curr_ws_events)) # Add it to redis
    await redis_db.publish(str(bot_id), orjson.dumps({id: ws_event})) # Publish it to consumers

class BotActions():
    class GeneratedObject():
        """
        Instead of crappily changing self, just use a generated object which is atleast cleaner
        """
        extra_owners = []
        tags = []

    def __init__(self, bot):
        self.__dict__.update(bot) # Add all kwargs to function
        if "bt" not in self.__dict__ or "user_id" not in self.__dict__:
            raise SyntaxError("Background Task and User ID must be in dict")

        self.generated = self.GeneratedObject() # To keep things clean, make sure we always put changed properties in generated

    async def base_check(self) -> Optional[str]:
        """Perform basic checks for adding/editting bots. A check returning None means success, otherwise error should be returned to client"""
        if self.bot_id == "" or self.prefix == "" or self.invite == "" or self.description == "" or self.long_description == "" or len(self.prefix) > 9: # Check base fields
            return "Please ensure you have filled out all the required fields and that your prefix is less than 9 characters.", 1

        if self.tags == "":
            return "You must select tags for your bot", 2 # Check tags

        if not self.banner.startswith("https://") and self.banner not in ["", "none"]:
            return "Your banner does not use https://. Please change it", 3 # Check banner and ensure HTTPS
        
        if not self.invite.startswith("https://discord.com") or "oauth" not in self.invite:
            return "Invalid Bot Invite: Your bot invite must be in the format of https://discord.com/api/oauth2... or https://discord.com/oauth2...", 4 # Invalid Invite

        if len(self.description) > 110:
            return "Your short description must be shorter than 110 characters", 5 # Short Description Check

        try:
            bot_object = await get_bot(self.bot_id) # Check if bot exists
        except:
            return "According to Discord's API and our cache, your bot does not exist. Please try again after 2 hours.", 6

        if not bot_object:
            return "According to Discord's API and our cache, your bot does not exist. Please try again after 2 hours.", 7
        
        if type(self.tags) != list:
            self.generated.tags = self.tags.split(",")
        else:
            self.generated.tags = self.tags # Generate tags either directly or made to list and then added to generated

        flag = False
        for test in self.generated.tags:
            if test not in TAGS:
                return "One of your tags doesn't exist internally. Please check your tags again", 8 # Check tags internally
            flag = True

        if not flag:
            return "You must select tags for your bot", 9 # No tags found

        if self.banner != "none" and self.banner != "":
            try:
                img = await requests.get(self.banner) # Check content type of banner
            except:
                img = None
            if img is None or img.headers.get("Content-Type") is None or img.headers.get("Content-Type").split("/")[0] != "image":
                return "Banner URL is not an image. Please make sure it is setting the proper Content-Type", 10

        if self.donate != "" and not (self.donate.startswith("https://patreon.com") or self.donate.startswith("https://paypal.me")):
            return "Only Patreon and Paypal.me are allowed for donation links as of right now.", 11 # Check donation link for approved source (paypal.me and patreon

        if self.extra_owners == "": # Generate extra owners list by either adding directly if list or splitting to list, removing extra ones
            self.generated.extra_owners = []
        else:
            if type(self.extra_owners) != list:
                self.generated.extra_owners = self.extra_owners.split(",")
            else:
                self.generated.extra_owners = self.extra_owners

        try:
            self.generated.extra_owners = [int(id.replace(" ", "")) for id in self.generated.extra_owners if int(id.replace(" ", "")) not in self.generated.extra_owners] # Remove extra ones and make all ints
        except:
            return "One of your extra owners doesn't exist or you haven't comma-seperated them.", 12

        if self.github != "" and not self.github.startswith("https://www.github.com"): # Check github for github.com if not empty string
            return "Your github link must start with https://www.github.com", 13

        self.privacy_policy = self.privacy_policy.replace("http://", "https://") # Force https on privacy policy
        if self.privacy_policy != "" and not self.privacy_policy.startswith("https://"): # Make sure we actually have a HTTPS privacy policy
            return "Your privacy policy must be a proper URL starting with https://. URLs which start with http:// will be automatically converted to HTTPS", 14

        if self.vanity == "": # Check if vanity is already being used or is reserved
            pass
        else:
            vanity_check = await db.fetchrow("SELECT DISTINCT vanity_url FROM vanity WHERE lower(vanity_url) = $1 AND redirect != $2", self.vanity.replace(" ", "").lower(), self.bot_id) # Get distinct vanitiss
            if vanity_check is not None or self.vanity.replace("", "").lower() in ["bot", "docs", "redoc", "doc", "profile", "server", "bots", "servers", "search", "invite", "discord", "login", "logout", "register", "admin"] or self.vanity.replace("", "").lower().__contains__("/"): # Check if reserved or in use
                return "Your custom vanity URL is already in use or is reserved", 15

    async def edit_check(self):
        """Perform extended checks for editting bots"""
        check = await self.base_check() # Initial base checks
        if check is not None:
            return check

        check = await is_bot_admin(int(self.bot_id), int(self.user_id)) # Check for owner
        if check is None:
            return "This bot doesn't exist in our database.", 16
        elif check is False:
            return "You aren't the owner of this bot.", 17

        check = await get_user(self.user_id)
        if check is None: # Check if owner exists
            return "You do not exist on the Discord API. Please wait for a few hours and try again", 18

    async def add_check(self):
        """Perform extended checks for adding bots"""
        check = await self.base_check() # Initial base checks
        if check is not None:
            return check # Base check erroring means return base check without continuing as string return means error

        if (await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1", self.bot_id)) is not None:
            return "This bot already exists on Fates List", 19 # Dont add bots which already exist

    async def add_bot(self):
        """Add a bot"""
        check = await self.add_check() # Perform add bot checks
        if check is not None:
            return check # Returning a strung and not None means error to be returned to consumer

        creation = time.time() # Creation Time

        self.bt.add_task(self.add_bot_bt, int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.generated.tags, self.generated.extra_owners, creation, self.invite, self.features, self.html_long_description, self.css, self.donate, self.github, self.webhook, self.webhook_type, self.vanity, self.privacy_policy, self.nsfw) # Add bot to queue as background task

    async def edit_bot(self):
        """Edit a bot"""
        check = await self.edit_check() # Perform edit bot checks
        if check is not None:
            return check

        creation = time.time() # Creation Time
        self.bt.add_task(self.edit_bot_bt, int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.generated.tags, self.generated.extra_owners, creation, self.invite, self.webhook, self.vanity, self.github, self.features, self.html_long_description, self.webhook_type, self.css, self.donate, self.privacy_policy, self.nsfw) # Add edit bot to queue as background task

    @staticmethod
    async def add_bot_bt(user_id, bot_id, prefix, library, website, banner, support, long_description, description, tags, extra_owners, creation, invite, features, html_long_description, css, donate, github, webhook, webhook_type, vanity, privacy_policy, nsfw):
        await db.execute("""INSERT INTO bots (
                bot_id, prefix, bot_library,
                invite, website, banner, 
                discord, long_description, description,
                tags, votes, servers, shard_count,
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
                $22, $23, $24)""", bot_id, prefix, library, invite, website, banner, support, long_description, description, tags, 0, 0, 0, int(creation), get_token(132), features, html_long_description, css, donate, github, webhook, webhook_type, privacy_policy, nsfw) # Add new bot info
        if vanity.replace(" ", "") != '':
            await db.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 1, vanity, bot_id) # Add new vanity if not empty string
        
        await db.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", bot_id, user_id, True) # Add new main bot owner
        extra_owners_add = [(bot_id, owner, False) for owner in extra_owners] # Create list of extra owner tuples for executemany executemany
        await db.executemany("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", extra_owners_add) # Add in one step

        await add_event(bot_id, "add_bot", {}) # Send a add_bot event to be succint and complete 
        owner = int(user_id)
        channel = client.get_channel(bot_logs)
        bot_name = (await get_bot(bot_id))["username"]
        add_embed = discord.Embed(title="New Bot!", description=f"<@{owner}> added the bot <@{bot_id}>({bot_name}) to queue!", color=0x00ff00)
        add_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{bot_id}")
        try:
            member = channel.guild.get_member(owner)
            if member is not None:
                await member.send(embed = add_embed) # Send user DM if possible

        except:
            pass
        await channel.send(f"<@&{staff_ping_add_role}>", embed = add_embed) # Send message with add bot ping

    @staticmethod
    async def edit_bot_bt(user_id, bot_id, prefix, library, website, banner, support, long_description, description, tags, extra_owners, creation, invite, webhook, vanity, github, features, html_long_description, webhook_type, css, donate, privacy_policy, nsfw):
        await db.execute("UPDATE bots SET bot_library=$2, webhook=$3, description=$4, long_description=$5, prefix=$6, website=$7, discord=$8, tags=$9, banner=$10, invite=$11, github = $12, features = $13, html_long_description = $14, webhook_type = $15, css = $16, donate = $17, privacy_policy = $18, nsfw = $19 WHERE bot_id = $1", bot_id, library, webhook, description, long_description, prefix, website, support, tags, banner, invite, github, features, html_long_description, webhook_type, css, donate, privacy_policy, nsfw) # Update bot with new info
        owners = await db.fetch("SELECT owner FROM bot_owner where bot_id = $1 AND main = false", bot_id)
        extra_owners_ignore = [] # Extra Owners to ignore because they have already been counted in the database (already extra owners)
        extra_owners_delete = [] # Extra Owners to delete
        extra_owners_add = [] # Extra Owners to add
        for owner in owners: # Loop through owners and add to delete list if not in new extra owners
            if owner["owner"] not in extra_owners:
                extra_owners_delete.append((bot_id, owner["owner"]))
            else:
                extra_owners_ignore.append(owner["owner"]) # Ignore this user when adding users
        await db.executemany("DELETE FROM bot_owner WHERE bot_id = $1 AND owner = $2", extra_owners_delete) # Delete in one step
        for owner in extra_owners:
            if owner not in extra_owners_ignore:
                extra_owners_add.append((bot_id, owner, False)) # If not in ignore list, add to add list
        await db.executemany("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", extra_owners_add) # Add in one step

        check = await db.fetchrow("SELECT vanity FROM vanity WHERE redirect = $1", bot_id) # Check vanity existance
        if check is None:
            if vanity.replace(" ", "") != '': # If not there for this bot, insert new one
                await db.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 1, vanity, bot_id)
        else:
            if vanity == '':
                vanity = None # If vanity is expty string, there is no vanity

            await db.execute("UPDATE vanity SET vanity_url = $1 WHERE redirect = $2", vanity, bot_id) # Update the vanity since bot already use it
        await add_event(bot_id, "edit_bot", {"user": str(user_id)}) # Send event
        channel = client.get_channel(bot_logs)
        owner = int(user_id)
        edit_embed = discord.Embed(title="Bot Edit!", description=f"<@{owner}> has edited the bot <@{bot_id}>!", color=0x00ff00)
        edit_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{bot_id}")
        await channel.send(embed = edit_embed) # Send message to channel

async def bot_auth(bot_id: int, api_token: str, *, fields: Optional[str] = None):
    if fields is None:
        return await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(api_token))
    return await db.fetchrow(f"SELECT bot_id, {fields} FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(api_token))

async def user_auth(user_id: int, api_token: str, fields: Optional[str] = None):
    if fields is None:
        return await db.fetchval("SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", user_id, str(api_token))
    return await db.fetchrow(f"SELECT user_id, {fields} FROM users WHERE user_id = $1 AND api_token = $2", user_id, str(api_token))

class BotListAdmin():
    def __init__(self, bot_id, mod):
        self.bot_id = bot_id
        self.mod = mod
        self.channel = client.get_channel(bot_logs)
        self.guild = self.channel.guild
    
    async def _get_main_owner(self):
        return await db.fetchrow("SELECT owner FROM bot_owner WHERE bot_id = $1 AND main = true", self.bot_id)

    async def approve_bot(self, feedback):
        owners = await db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", self.bot_id)
        if owners is None:
            return False
        await db.execute("UPDATE bots SET state = 0 WHERE bot_id = $1", self.bot_id)
        await add_event(self.bot_id, "approve", {"user": self.mod})
        owner = [obj["owner"] for obj in owners if obj["main"]][0]
        approve_embed = discord.Embed(title="Bot Approved!", description = f"<@{self.bot_id}> by <@{owner}> has been approved", color=0x00ff00)
        approve_embed.add_field(name="Feedback", value=feedback)
        approve_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}")
        bot_dev = self.guild.get_role(bot_dev_role)
        for _owner in owners:
            try:
                member = self.guild.get_member(int(_owner['owner']))
                if member is not None:
                    await member.add_roles(bot_dev)
            except:
                pass
                
        try:
            member = self.guild.get_member(int(owner))
            if member is not None:
                await member.send(embed = approve_embed)
        except:
            pass
        await self.channel.send(embed = approve_embed)

        # Give Bot Dev Roles
        for owner in owners:
            try:
                member = guild.get_member(int(owner))
            except:
                member = None
                if member is None:
                    pass
                else:
                    await member.add_roles(guild.get_role(bot_dev_role))

    async def unverify_bot(self, reason):
        owner = await self._get_main_owner()
        if owner is None:
            return False
        await db.execute("UPDATE bots SET state = 1, banned = false WHERE bot_id = $1", self.bot_id)
        await add_event(self.bot_id, "unverify", {"user": self.mod})
        unverify_embed = discord.Embed(title="Bot Unverified!", description = f"<@{self.bot_id}> by <@{owner['owner']}> has been unverified", color=discord.Color.red())
        unverify_embed.add_field(name="Reason", value=reason)
        await self.channel.send(embed = unverify_embed)

    async def deny_bot(self, reason):
        owner = await self._get_main_owner()
        if owner is None:
            return False
        await db.execute("UPDATE bots SET state = 2 WHERE bot_id = $1", self.bot_id)
        await add_event(self.bot_id, "ban", {"user": self.mod, "type": "deny"})
        deny_embed = discord.Embed(title="Bot Denied!", description = f"<@{self.bot_id}> by <@{owner['owner']}> has been denied", color=discord.Color.red())
        deny_embed.add_field(name="Reason", value=reason)
        await self.channel.send(embed = deny_embed)
        try:
            member = self.guild.get_member(int(owner["owner"]))
            if member is not None:
                await member.send(embed = deny_embed)
        except:
            pass

    async def ban_bot(self, reason):
        ban_embed = discord.Embed(title="Bot Banned", description=f"<@{self.bot_id}> has been banned", color=discord.Color.red())
        ban_embed.add_field(name="Reason", value = reason)
        await self.channel.send(embed = ban_embed)
        try:
            await self.guild.kick(self.guild.get_member(self.bot_id))
        except:
            pass
        await db.execute("UPDATE bots SET state = 4 WHERE bot_id = $1", self.bot_id)
        await add_event(self.bot_id, "ban", {"user": self.mod})

    async def unban_bot(self, state):
        if state == 2:
            word = "removed from the deny list"
            title = "Bot requeued"
        else:
            word = "unbanned"
            title = "Bot unbanned"
        unban_embed = discord.Embed(title=title, description=f"<@{self.bot_id}> has been {word}", color=0x00ff00)
        await self.channel.send(embed = unban_embed)
        if state == 2:
            await db.execute("UPDATE bots SET state = 1 WHERE bot_id = $1", self.bot_id)
        else:
            await db.execute("UPDATE bots SET state = 0 WHERE bot_id = $1", self.bot_id)
            await add_event(self.bot_id, "unban", {"user": self.mod})
