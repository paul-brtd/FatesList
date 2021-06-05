"""Modules to move"""
# TODO: Move these
from modules.core import *
from uuid import UUID
from fastapi.responses import HTMLResponse
from typing import List, Dict
from modules.discord.api.v2.modelstomove import * #TODO
from modules.models.bot_actions import BotAdd, BotEdit
from lxml.html.clean import Cleaner
from modules.badges import get_badges
discord_o = Oauth(OauthConfig)

cleaner = Cleaner(remove_unknown_tags=False)

API_VERSION = 2 # This is the API version

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - To Move"]
)

@router.get("/bots/{bot_id}/token")
async def get_bot_token(request: Request, bot_id: int, user_id: int, Authorization: str = Header("USER_TOKEN")):
    """
    Gets a bot token given a user token. 401 = Invalid API Token, 403 = Forbidden (not owner of bot or staff)
    """
    id = await user_auth(user_id, Authorization)
    if id is None:
        return abort(401)
    bot_admin = await is_bot_admin(bot_id, user_id)
    if not bot_admin:
        return abort(403)
    return await db.fetchrow("SELECT api_token FROM bots WHERE bot_id = $1", bot_id)

@router.patch("/bots/{bot_id}/token", response_model = APIResponse)
async def regenerate_bot_token(request: Request, bot_id: int, Authorization: str = Header("BOT_TOKEN")):
    """
    Regenerates the Bot token

    **Bot Token**: You can get this by clicking your bot and clicking edit and clicking Show (under API Token section)
    """
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    await db.execute("UPDATE bots SET api_token = $1 WHERE bot_id = $2", get_token(132), id)
    return {"done": True, "reason": None, "code": 1000}

@router.get("/bots/random", response_model = BotRandom, dependencies=[Depends(RateLimiter(times=7, seconds=5))])
async def random_bots_api(request: Request):
    random_unp = await db.fetchrow("SELECT description, banner, state, votes, servers, bot_id, invite FROM bots WHERE state = 0 OR state = 6 ORDER BY RANDOM() LIMIT 1") # Unprocessed, use the random function to get a random bot
    try:
        bot = (await get_bot(random_unp["bot_id"])) | dict(random_unp) # Get bot from cache and add that in
    except:
        return await random_bots_api(request) 
    bot["bot_id"] = str(bot["bot_id"]) # Make sure bot id is a string to prevent corruption issues
    bot["servers"] = human_format(bot["servers"]) # Format the servers field
    bot["description"] = cleaner.clean_html(bot["description"]) # Prevent some basic attacks in short description
    if bot["banner"] is None:
        bot["banner"] = "" # Make sure banner is always a string
    return bot

@router.get("/bots/{bot_id}", response_model = Bot, dependencies=[Depends(RateLimiter(times=5, minutes=3))])
async def get_bot_api(request: Request, bot_id: int):
    """Gets bot information given a bot ID. If not found, 404 will be returned."""
    api_ret = await db.fetchrow("SELECT banner, description, long_description_type, long_description, servers AS server_count, shard_count, shards, prefix, invite, invite_amount, features, bot_library AS library, state, website, discord AS support, github, user_count, votes, css, donate, privacy_policy, nsfw FROM bots WHERE bot_id = $1", bot_id)
    if api_ret is None:
        return abort(404)
    api_ret = dict(api_ret)
    tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
    api_ret["tags"] = [tag["tag"] for tag in tags]
    owners = await db.fetch("SELECT DISTINCT ON (owner) owner, main FROM bot_owner WHERE bot_id = $1 ORDER BY owner", bot_id)
    _owners = []
    # Preperly sort owners
    for owner in owners:
        if owner["main"]: _owners.insert(0, owner)
        else: _owners.append(owner)
    owners = _owners

    api_ret["owners"] = [{"user": (await get_user(obj["owner"])), "main": obj["main"]} for obj in _owners]
    if api_ret["features"] is None:
        api_ret["features"] = []
    api_ret["invite_link"] = await invite_bot(bot_id, api = True)
    bot_obj = await get_bot(bot_id)
    if bot_obj is None:
        return abort(404)
    api_ret = api_ret | bot_obj
    api_ret["vanity"] = await db.fetchval("SELECT vanity_url FROM vanity WHERE redirect = $1", bot_id)
    return api_ret

@router.get("/bots/{bot_id}/widget")
async def bot_widget_api(request: Request, bot_id: int, bt: BackgroundTasks):
    return await render_bot_widget(request, bt, bot_id, api = True)

@router.get("/bots/{bot_id}/raw")
async def get_raw_bot_api(request: Request, bot_id: int, bt: BackgroundTasks):
    """
    Gets the raw given to the template with a few differences (bot_id being string and not int and passing auth manually to the function (coming soon) as the API aims to be as stateless as possible)

    Note that you likely want the Get Bot API and not this in most cases

    This API is prone to change as render_bot will keep changing
    """
    return await render_bot(request, bt, bot_id, api = True)

@router.get("/bots/{bot_id}/events", response_model = BotEvents)
async def get_bot_events_api(request: Request, bot_id: int, exclude: Optional[list] = None, filter: Optional[list] = None, Authorization: str = Header("BOT_TOKEN_OR_TEST_MANAGER_KEY")):
    if secure_strcmp(Authorization, test_server_manager_key):
        pass
    else:
        id = await bot_auth(bot_id, Authorization)
        if id is None:
            return abort(401)
    return await bot_get_events(bot_id = bot_id, filter = filter, exclude = exclude)

@router.get("/bots/{bot_id}/ws_events")
async def get_bot_ws_events(request: Request, bot_id: int, Authorization: str = Header("BOT_TOKEN_OR_TEST_MANAGER_KEY")):
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    ini_events = {}
    events = await redis_db.hget(str(bot_id), key = "ws")
    if events is None:
        events = {} # Nothing
    return events

@router.post("/bots/{bot_id}", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=1, minutes=2))])
async def add_bot_api(request: Request, bot_id: int, bot: BotAdd, Authorization: str = Header("USER_TOKEN_OR_BOTBLOCK_ADD_KEY")):
    if secure_strcmp(Authorization, bb_add_key):
        bot.oauth_enforced = True # Botblock add key, enforce oauth
    else:
        try:
            user = await user_auth(int(bot.owner), Authorization)
        except:
            return abort(401)
        if user is None:
            return abort(401)
    if bot.oauth_enforced:
        user_json = await discord_o.get_user_json(bot.oauth_access_token)
        if user_json.get("id") is None or str(user_json.get("id")) != str(user):
            return abort(401) # OAuth abort
    bot.banner = bot.banner.replace("http://", "https://").replace("(", "").replace(")", "")
    bot_dict = bot.dict()
    bot_dict["bot_id"] = bot_id
    bot_dict["user_id"] = bot_dict["owner"]
    bot_adder = BotActions(bot_dict)
    rc = await bot_adder.add_bot()
    if rc is None:
        return {"done": True, "reason": f"{site_url}/bot/{bot_id}", "code": 1001}
    return ORJSONResponse({"done": False, "reason": rc[0],"code": rc[1]}, status_code = 400)

@router.patch("/bots/{bot_id}", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=1, minutes=2))])
async def edit_bot_api(request: Request, bot_id: int, bot: BotEdit, Authorization: str = Header("USER_TOKEN_OR_BOTBLOCK_EDIT_KEY")):
    """
    Edits a bot, the owner here should be the owner editing the bot
    """
    if secure_strcmp(Authorization, bb_edit_key):
        bot.oauth_enforced = True # Botblock add key, enforce o0auth0
    else:
        try:
            user = await user_auth(int(bot.owner), Authorization)
        except:
            return abort(401)
        if user is None:
            return abort(401)
    if bot.oauth_enforced:
        user_json = await discord_o.get_user_json(bot.oauth_access_token)
        if user_json.get("id") is None or str(user_json.get("id")) != str(user):
            return abort(401) # OAuth abort
    bot.banner = bot.banner.replace("http://", "https://").replace("(", "").replace(")", "")
    bot_dict = bot.dict()
    bot_dict["bot_id"] = bot_id
    bot_dict["user_id"] = bot_dict["owner"]
    bot_editor = BotActions(bot_dict)
    rc = await bot_editor.edit_bot()
    if rc is None:
        return {"done": True, "reason": f"{site_url}/bot/{bot_id}", "code": 1001}
    return ORJSONResponse({"done": False, "reason": rc[0], "code": rc[1]}, status_code = 400)

@router.get("/bots/{bot_id}/reviews", response_model = BotReviews)
async def get_bot_reviews(request: Request, bot_id: int, page: Optional[int] = 1):
    reviews = await parse_reviews(bot_id, page = page)
    if reviews[0] == []:
        return abort(404)
    return {"reviews": reviews[0], "average_stars": reviews[1], "pager": {"total_count": reviews[2], "total_pages": reviews[3], "per_page": reviews[4], "from": ((page - 1) * reviews[4]) + 1, "to": (page - 1) * reviews[4] + len(reviews[0])}}

@router.patch("/bots/{bot_id}/reviews/{rid}/votes", response_model = APIResponse)
async def vote_review_api(request: Request, bot_id: int, rid: uuid.UUID, vote: BotReviewVote, Authorization: str = Header("USER_TOKEN")):
    id = await user_auth(vote.user_id, Authorization)
    if id is None:
        return abort(401)
    vote.user_id = int(vote.user_id)
    bot_rev = await db.fetchrow("SELECT review_upvotes, review_downvotes, star_rating, reply, review_text FROM bot_reviews WHERE id = $1", rid)
    if bot_rev is None:
        return ORJSONResponse({"done": False, "reason": "You are not allowed to up/downvote this review (doesn't actually exist)", "code": 3836}, status_code = 404)
    bot_rev = dict(bot_rev)
    if vote.upvote:
        main_key = "review_upvotes"
        remove_key = "review_downvotes"
    else:
        main_key = "review_downvotes"
        remove_key = "review_upvotes"
    if vote.user_id in bot_rev[main_key]:
        return ORJSONResponse({"done": False, "reason": "The user has already voted for this review", "code": 5858}, status_code = 400)
    if vote.user_id in bot_rev[remove_key]:
        while True:
            try:
                bot_rev[remove_key].remove(vote.user_id)
            except:
                break
    bot_rev[main_key].append(vote.user_id)
    await db.execute("UPDATE bot_reviews SET review_upvotes = $1, review_downvotes = $2 WHERE id = $3", bot_rev["review_upvotes"], bot_rev["review_downvotes"], rid)
    await bot_add_event(bot_id, enums.APIEvents.review_vote, {"user": str(vote.user_id), "id": str(rid), "star_rating": bot_rev["star_rating"], "reply": bot_rev["reply"], "review": bot_rev["review_text"], "upvotes": len(bot_rev["review_upvotes"]), "downvotes": len(bot_rev["review_downvotes"]), "upvote": vote.upvote})
    return {"done": True, "reason": None, "code": 1000}

@router.delete("/bots/{bot_id}/reviews/{rid}", response_model = APIResponse)
async def delete_review(request: Request, bot_id: int, rid: uuid.UUID, bt: BackgroundTasks, data: BotReviewAction, Authorization: str = Header("USER_TOKEN")):
    id = await user_auth(data.user_id, Authorization)
    if id is None:
        return abort(401)
    data.user_id = int(data.user_id)
    guild = client.get_guild(main_server)
    user = guild.get_member(data.user_id)
    if user is None:
        staff = False 
    else:
        staff = is_staff(staff_roles, user.roles, 2)[0]
    if staff:
        check = await db.fetchrow("SELECT replies FROM bot_reviews WHERE id = $1", rid)
        if check is None:
            return ORJSONResponse({"done": False, "reason": "You are not allowed to delete this review", "code": 1232}, status_code = 400)
    else:
        check = await db.fetchrow("SELECT replies FROM bot_reviews WHERE id = $1 AND bot_id = $2 AND user_id = $3", rid, bot_id, data.user_id)
        if check is None:
            return ORJSONResponse({"done": False, "reason": "You are not allowed to delete this review", "code": 1232}, status_code = 400)
    event_data = await db.fetchrow("SELECT reply, review_text, star_rating FROM bot_reviews WHERE id = $1", rid) # Information needed to send an event
    await db.execute("DELETE FROM bot_reviews WHERE id = $1", rid)
    await bot_add_event(bot_id, enums.APIEvents.review_delete, {"user": str(data.user_id), "reply": event_data["reply"], "id": str(rid), "star_rating": event_data["star_rating"], "review": event_data["review_text"]})
    return {"done": True, "reason": None, "code": 1000}

@router.get("/bots/{bot_id}/commands", response_model = BotCommandsGet)
async def get_bot_commands_api(request:  Request, bot_id: int, filter: Optional[str] = None):
    cmd = await get_bot_commands(bot_id, filter)
    if cmd == {}:
        return abort(404)
    return cmd

@router.post("/bots/{bot_id}/commands", response_model = BotCommandAddResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def add_bot_command_api(request: Request, bot_id: int, command: PartialBotCommand, Authorization: str = Header("BOT_TOKEN"), force_add: Optional[bool] = False):
    """
        Self explaining command. Note that if force_add is set, the API will not check if your command already exists and will forcefully add it, this may lead to duplicate commands on your bot. If ret_id is not set, you will not get the command id back in the api response
    """
    try:
        _tmp = enums.CommandType(command.cmd_type)
    except ValueError:
        return ORJSONResponse({"done":  False, "reason": "UNSUPPORTED_MODE"}, status_code = 400)

    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)

    if force_add is False:
        check = await db.fetchrow("SELECT name FROM bot_commands WHERE name = $1 AND bot_id = $2", command.name, bot_id)
        if check is not None:
            return ORJSONResponse({"done":  False, "reason": "COMMAND_ALREADY_EXISTS"}, status_code = 400)
    id = uuid.uuid4()
    await db.execute("INSERT INTO bot_commands (id, bot_id, cmd_groups, cmd_type, name, description, args, examples, premium_only, notes, doc_link) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)", id, bot_id, command.cmd_groups, command.cmd_type, command.name, command.description, command.args, command.examples, command.premium_only, command.notes, command.doc_link)
    await bot_add_event(bot_id, enums.APIEvents.command_add, {"user": None, "id": id})
    return ORJSONResponse({"done": True, "reason": None, "id": id, "code": 1001}, status_code = 206)

@router.patch("/bots/{bot_id}/commands", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def edit_bot_command_api(request: Request, bot_id: int, command: BotCommand, Authorization: str = Header("BOT_TOKEN")):
    try:
        _tmp = enums.CommandType(command.cmd_type)
    except ValueError:
        return ORJSONResponse({"done":  False, "reason": "UNSUPPORTED_MODE"}, status_code = 400)

    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    data = await db.fetchrow(f"SELECT id, cmd_type, cmd_groups, name, description, args, examples, premium_only, notes, doc_link FROM bot_commands WHERE id = $1 AND bot_id = $2", command.id, bot_id)
    if data is None:
        return abort(404)

    # Check values to be editted
    command_dict = command.dict()
    for key in command_dict.keys():
        if command_dict[key] is None: 
            command_dict[key] = data[key]
    await db.execute("UPDATE bot_commands SET cmd_type = $2, name = $3, description = $4, args = $5, examples = $6, premium_only = $7, notes = $8, doc_link = $9, cmd_groups = $10 WHERE id = $1", command_dict["id"], command_dict["cmd_type"], command_dict["name"], command_dict["description"], command_dict["args"], command_dict["examples"], command_dict["premium_only"], command_dict["notes"], command_dict["doc_link"], command_dict["cmd_groups"])
    await bot_add_event(bot_id, enums.APIEvents.command_edit, {"user": None, "id": command.id})
    return {"done": True, "reason": None, "code": 1000}

@router.delete("/bots/{bot_id}/commands", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def delete_bot_command_api_(request: Request, bot_id: int, command: BotCommandDelete, Authorization: str = Header("BOT_TOKEN")):
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    await db.execute("DELETE FROM bot_commands WHERE id = $1 AND bot_id = $2", command.id, bot_id)
    await bot_add_event(bot_id, enums.APIEvents.command_delete, {"user": None, "id": command.id})
    return {"done": True, "reason": None, "code": 1000}

@router.get("/bots/{bot_id}/votes", response_model = BotVoteCheck, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
async def get_votes_api(request: Request, bot_id: int, user_id: int, Authorization: str = Header("BOT_TOKEN")):
    """Endpoint to check amount of votes a user has."""
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    voter_count = await db.fetchval("SELECT cardinality(timestamps) FROM bot_voters WHERE bot_id = $1 AND user_id = $2", int(bot_id), int(user_id))
    voter_count = voter_count if voter_count else 0
    ret = await vote_bot(user_id = user_id, bot_id = bot_id, autovote = False, test = False, pretend = True)
    if ret is None:
        {"votes": voter_count, "voted": voter_count != 0, "vote_epoch": 0, "time_to_vote": 0, "vote_right_now": False, "message": "Voter not found!"}
    return {"votes": voter_count, "voted": voter_count != 0, "vote_epoch": ret[0].timestamp() if isinstance(ret, tuple) else 0, "time_to_vote": ret[1].total_seconds() if isinstance(ret, tuple) else 0, "vote_right_now": ret == True,  "message": None}

@router.post("/bots/{bot_id}/votes/test")
async def send_test_webhook(bot_id: int, Authorization: str = Header("BOT_TOKEN")):
    """Endpoint to test webhooks"""
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    return await vote_bot(user_id = 519850436899897346, bot_id = bot_id, autovote = False, test = True, pretend = False) 

@router.get("/bots/{bot_id}/votes/timestamped", response_model = BotVotesTimestamped)
async def timestamped_get_votes_api(request: Request, bot_id: int, user_id: Optional[int] = None, Authorization: str = Header("BOT_TOKEN")):
    """Endpoint to check amount of votes a user has with timestamps. This does not return whether a user can vote"""
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    elif user_id is not None:
        ldata = await db.fetch("SELECT user_id, timestamps FROM bot_voters WHERE bot_id = $1 AND user_id = $2", int(bot_id), int(user_id))
    else:
        ldata = await db.fetch("SELECT user_id, timestamps FROM bot_voters WHERE bot_id = $1", int(bot_id))
    ret = {}
    for data in ldata:
        ret[str(data["user_id"])] = [round(ts.timestamp()) for ts in data["timestamps"]]
    return {"timestamped_votes": ret}

@router.post("/bots/{bot_id}/stats", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=5, minutes=1))], tags = [f"Core (API v{API_VERSION})"])
async def set_bot_stats_api(request: Request, bot_id: int, api: BotStats, Authorization: str = Header("BOT_API_TOKEN")):
    """
    This endpoint allows you to set the guild + shard counts for your bot
    """
    id = await bot_auth(bot_id, Authorization, fields = "shard_count, shards, user_count")
    if id is None:
        return abort(401)
    if api.shard_count is None:
        shard_count = id["shard_count"]
    else:
        shard_count = api.shard_count
    if api.shards is None:
        shards = id["shards"]
    else:
        shards = api.shards
    if api.user_count is None:
        user_count = id["user_count"]
    else:
        user_count = api.user_count
    await set_stats(bot_id = id["bot_id"], guild_count = api.guild_count, shard_count = shard_count, shards = shards, user_count = user_count)
    return {"done": True, "reason": None, "code": 1000}

@router.get("/bots/{bot_id}/maintenance", response_model = BotMaintenance)
async def get_maintenance_mode(request: Request, bot_id: int):
    ret = await get_maint(bot_id = bot_id)
    if ret.get("fail"):
        return abort(404)
    return ret

@router.post("/bots/{bot_id}/maintenance", response_model = APIResponse)
async def set_maintenance_mode(request: Request, bot_id: int, api: BotMaintenancePartial, Authorization: str = Header("BOT_TOKEN")):
    """This is just an endpoing for enabling or disabling maintenance mode. As of the new API Revamp, this is the only way to enable or disable maintenance mode as of right now

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token

    **Mode**: Whether you want to enter or exit maintenance mode. Setting this to 1 will enable maintenance, setting this to 2 will enable long-lasting maintenance mode and setting this to 0 will disable maintenance mode. More flying in soon :)
    """
    
    if api.mode not in [0, 1]:
        return ORJSONResponse({"done":  False, "reason": "UNSUPPORTED_MODE"}, status_code = 400)

    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    await add_maint(id["bot_id"], api.mode, api.reason)
    return {"done": True, "reason": None, "code": 1000}

@router.get("/features/{name}", response_model = FLFeature)
async def get_feature_api(request: Request, name: str):
    """Gets a feature given its internal name (custom_prefix, open_source etc)"""
    if name not in features.keys():
        return abort(404)
    return features[name]

@router.get("/tags/{name}", response_model = FLTag)
async def get_tags_api(request: Request, name: str):
    """Gets a tag given its internal name (custom_prefix, open_source etc)"""
    if name not in TAGS.keys():
        return abort(404)
    return {"name": name.replace("_", " ").title(), "iconify_data": TAGS[name], "id": name}

@router.get("/code/{vanity}", response_model = BotVanity)
async def get_vanity_api(request: Request, vanity: str):
    vb = await vanity_bot(vanity)
    logger.trace(f"Vanity is {vanity} and vb is {vb}")
    if vb is None:
        return abort(404)
    return {"type": vb[1], "redirect": str(vb[0])}

@router.get("/index/bots", response_model = BotIndex)
async def bots_index_page(request: Request, csrf_protect: CsrfProtect = Depends()):
    """For any potential Android/iOS app, crawlers etc."""
    return await render_index(request = request, api = True, csrf_protect = csrf_protect)

@router.get("/search/bots", response_model = BotSearch)
async def bots_search_page(request: Request, q: str):
    """For any potential Android/iOS app, crawlers etc. Q is the query to search for"""
    return await render_search(request = request, q = q, api = True)

@router.get("/search/profiles", response_model = ProfileSearch)
async def profiles_search_page(request: Request, q: str):
    """For any potential Android/iOS app, crawlers etc. Q is the query to search for"""
    return await render_profile_search(request = request, q = q, api = True)

@router.post("/preview", response_model = PrevResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def preview_api(request: Request, data: PrevRequest):
    if not data.html_long_description:
        html = emd(markdown.markdown(data.data, extensions=["extra", "abbr", "attr_list", "def_list", "fenced_code", "footnotes", "tables", "admonition", "codehilite", "meta", "nl2br", "sane_lists", "toc", "wikilinks", "smarty", "md_in_html"]))
    else:
        html = data.data
    # Take the h1...h5 anad drop it one lower
    html = html.replace("<h1", "<h2 style='text-align: center'").replace("<h2", "<h3").replace("<h4", "<h5").replace("<h6", "<p").replace("<a", "<a class='long-desc-link'").replace("ajax", "").replace("http://", "https://").replace(".alert", "")
    return {"html": html}

@router.get("/users/{user_id}")
async def get_user_api(request: Request, user_id: int):
    user = await db.fetchrow("SELECT badges, state, description, css FROM users WHERE user_id = $1", user_id)
    if user is None or user["state"] == enums.UserState.ddr_ban:
        return abort(404)
    user_obj = await get_user(user_id)
    if user_obj is None:
        return abort(404)
    user_ret = dict(user)
    badges = user_ret["badges"]
    del user_ret["badges"]
    _bots = await db.fetch("SELECT bots.description, bots.prefix, bots.banner, bots.state, bots.votes, bots.servers, bots.bot_id, bots.nsfw, bot_owner.main FROM bots INNER JOIN bot_owner ON bot_owner.bot_id = bots.bot_id WHERE bot_owner.owner = $1", user_id)
    bots = [dict(obj) | {"invite": await invite_bot(obj["bot_id"], api = True)} for obj in _bots]
    approved_bots = [obj for obj in bots if obj["state"] in (0, 6)]
    certified_bots = [obj for obj in bots if obj["state"] == 6]
    guild = client.get_guild(main_server)
    if guild is None:
        return abort(503)
    user_dpy = guild.get_member(int(user_id))
    if user_dpy is None:
        user_dpy = await client.fetch_user(user_id)
    if user_dpy is None: # Still connecting to dpy or whatever
        badges = None # Still not prepared to deal with it since we havent connected to discord yet 
    else:
        badges = get_badges(user_dpy, badges, approved_bots)
    return {"bots": bots, "approved_bots": approved_bots, "certified_bots": certified_bots, "bot_developer": approved_bots != [], "certified_developer": certified_bots != [], "profile": user_ret, "badges": badges, "defunct": user_dpy is None} | user_obj

@router.patch("/users/{user_id}/bots/{bot_id}/reminders")
async def set_vote_reminder(request: Request, user_id: int, bot_id: int, data: VoteReminderPatch, Authorization: str = Header("USER_TOKEN")):
    id = await user_auth(user_id, Authorization)
    if id is None:
        return abort(401)
    if data.remind:
        check = await db.fetchval("SELECT DISTINCT bot_id FROM user_reminders WHERE user_id = $1 AND bot_id = $2", user_id, bot_id)
        if check == 0:
            await db.execute("INSERT INTO user_reminders (user_id, bot_id) VALUES ($1, $2)", user_id, bot_id)
            return {"done": True, "reason": None, "code": 1000}
        else:
            return ORJSONResponse({"done": False, "reason": "User already signed up for vote reminders", "code": 37373}, status_code = 400)
    else:
        await db.execute("DELETE FROM user_reminders WHERE user_id = $1 AND bot_id = $2", user_id, bot_id)
        return {"done": True, "reason": None, "code": 1000}

@router.post("/users/{user_id}/servers/prepare", dependencies=[Depends(RateLimiter(times=3, seconds=35))], response_model = ServerListAuthed)
async def prepare_servers_api(request: Request, user_id: int, data: ServerCheck, Authorization: str = Header("USER_TOKEN")):
    """
    Prepares a user to add servers and returns available servers for said user. Scopes must have guild permission

    This request may change the access token and this should be set on the client and will be returned in the json response as well
    """
    id = await user_auth(user_id, Authorization)
    if id is None:
        return abort(401)
    valid = {}
    access_token = await discord_o.access_token_check(data.scopes, data.access_token.dict())
    request.session["access_token"] = access_token
    access_token["current_time"] = str(access_token["current_time"])
    servers = await discord_o.get_guilds(access_token["access_token"], permissions = [0x8, 0x20]) # Check for all guilds with 0x8 and 0x20
    for server in servers:
        try:
            guild = client_servers.get_guild(int(server))
        except:
            guild = None
        if guild is None:
            continue
        try:
            member = guild.get_member(int(user_id))
        except:
            member = None
        if member is None:
            continue
        if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
            logger.debug(f"Adding {guild.id} to prepared server list")
            guild_json = {"icon": str(guild.icon_url), "name": guild.name, "member_count": guild.member_count, "created_at": str(guild.created_at.timestamp()), "code": get_token(37)}
            await redis_db.hset(str(guild.id), key = "cache", value = orjson.dumps(guild_json))
            valid = valid | {str(guild.id): guild_json}
    logger.debug(f"Valid servers are {valid}")
    return {"servers": valid, "access_token": access_token}

@router.post("/servers/{guild_id}")
async def add_guild_api(request: Request, guild_id: int, user_id: int, data: ServersAdd, Authorization: str = Header("USER_TOKEN")):
    id = await user_auth(user_id, Authorization)
    if id is None:
        return abort(401)
    guild_data = await redis_db.hget(str(guild_id), key = "cache")
    if guild_data is None:
        logger.trace(f"Guild data is {guild_data}")
        return abort(404)
    guild_data = orjson.loads(guild_data)
    if guild_data["code"] != data.code:
        return ORJSONResponse({"done": False, "reason": "Bad code provided", "code": 6767}, status_code = 400)
    server_actions = ServerActions(data.dict() | {"data": guild_data, "guild_id": guild_id, "user_id": user_id})
    rc = await server_actions.add_server()
    if rc is None:
        return {"done": True, "reacon": None, "code": 1000}
    return ORJSONResponse({"done": False, "reason": rc[0], "code": rc[1]}, status_code = 400)

@router.patch("/users/{user_id}/description", response_model = APIResponse)
async def set_user_description_api(request: Request, user_id: int, desc: UserDescEdit, Authorization: str = Header("USER_TOKEN")):
    id = await user_auth(user_id, Authorization)
    if id is None:
        return abort(401)
    await db.execute("UPDATE users SET description = $1 WHERE user_id = $2", desc.description, user_id)
    return {"done": True, "reason": None, "code": 1000}

@router.patch("/users/{user_id}/token", response_model = APIResponse)
async def regenerate_user_token(request: Request, user_id: int, Authorization: str = Header("USER_TOKEN")):
    """Regenerate the User API token

    ** User API Token**: You can get this by clicking your profile and scrolling to the bottom and you will see your API Token
    """
    id = await user_auth(user_id, Authorization)
    if id is None:
        return abort(401)
    await db.execute("UPDATE users SET api_token = $1 WHERE user_id = $2", get_token(132), id)
    return {"done": True, "reason": None, "code": 1000}

# TODO: Paypal

# Generic methods to add coins for future paypal integration

async def create_order(user_id, quantity, token, id, lm):
    await db.execute("INSERT INTO user_payments (user_id, token, coins, paid, stripe_id, livemode) VALUES ($1, $2, $3, $4, $5, $6)", user_id, token, quantity, False, id, lm)
    try:
        guild = client.get_guild(main_server)
        user = guild.get_member(user_id)
        await user.send(f"You have successfully created an order for {quantity} coins! Your payment id is {id}. After our payment processor confirms your payment. The coins will be added to your account! DM a Fates List Admin with your payment id if you do not get the coins within an hour.")
    except:
        pass

async def fulfill_order(user_id, quantity, token, id, lm):
    await db.execute(f"UPDATE users SET coins = coins + {quantity} WHERE user_id = $1", user_id)
    await db.execute("UPDATE user_payments SET paid = $1 WHERE user_id = $2 AND token = $3", True, user_id, token) 
    try:
        guild = client.get_guild(main_server)
        user = guild.get_member(user_id)
        await user.send(f"We have successfully fulfilled an order for {quantity} coins! Your payment id is {id}. The coins have been added to your account! DM a Fates List Admin with your payment id if you did not get the coins.")
    except:
        pass

async def dm_customer_about_failed_payment(session):
    logger.debug(f"DM Customer: {session}")


