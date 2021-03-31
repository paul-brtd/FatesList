from ..deps import *
from uuid import UUID
from fastapi.responses import HTMLResponse
from typing import List, Dict
from modules.models.api_v2 import *

discord_o = Oauth(OauthConfig)

router = APIRouter(
    prefix = "/api/v2",
    include_in_schema = True,
    tags = ["API v2 (default, beta, freeze-soon)"]
)

@router.get("/bots/{bot_id}/promotions", response_model = BotPromotionGet, responses = {
    404: {"model": BotPromotion_NotFound} # Promotion Not Found
})
async def get_promotion(request:  Request, bot_id: int):
    promos = await get_promotions(bot_id)
    if promos == []:
        return ORJSONResponse(BotPromotion_NotFound().dict(), status_code = 404)
    return {"promotions": promos}

@router.post("/bots/{bot_id}/promotions", response_model = APIResponse)
async def add_promotion_api(request: Request, bot_id: int, promo: BotPromotionPartial, Authorization: str = Header("INVALID_API_TOKEN")):
    """Creates a promotion for a bot. Type can be 1 for announcement, 2 for promotion or 3 for generic

    """
    if len(promo.title) < 3:
        return ORJSONResponse({"done":  False, "reason": "TEXT_TOO_SMALL"}, status_code = 400)
    if promo.type not in [1, 2, 3]:
        return ORJSONResponse({"done":  False, "reason": "INVALID_PROMO_TYPE"}, status_code = 400)
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    id = id["bot_id"]
    await add_promotion(id, promo.title, promo.info, promo.css, promo.type)
    return {"done":  True, "reason": None}

@router.patch("/bots/{bot_id}/promotions", response_model = APIResponse)
async def edit_promotion(request: Request, bot_id: int, promo: BotPromotion, Authorization: str = Header("INVALID_API_TOKEN")):
    """Edits an promotion for a bot given its promotion ID.

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Promotion ID**: This is the ID of the promotion you wish to edit 

    """
    if len(promo.title) < 3:
        return ORJSONResponse({"done":  False, "reason": "TEXT_TOO_SMALL"}, status_code = 400)
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    pid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1 AND bot_id = $2", promo.id, bot_id)
    if pid is None:
        return ORJSONResponse({"done":  False, "reason": "NO_PROMOTION_FOUND"}, status_code = 400)
    await db.execute("UPDATE bot_promotions SET title = $1, info = $2 WHERE bot_id = $3 AND id = $4", promo.title, promo.info, bot_id, promo.id)
    return {"done": True, "reason": None}

@router.delete("/bots/{bot_id}/promotions", response_model = APIResponse)
async def delete_promotion(request: Request, bot_id: int, promo: BotPromotionDelete, Authorization: str = Header("INVALID_API_TOKEN")):
    """Deletes a promotion for a bot or deletes all promotions from a bot (WARNING: DO NOT DO THIS UNLESS YOU KNOW WHAT YOU ARE DOING).

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Event ID**: This is the ID of the event you wish to delete. Not passing this will delete ALL events, so be careful
    """
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    id = id["bot_id"]
    if promo.id is not None:
        eid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1", promolid)
        if eid is None:
            return ORJSONResponse({"done":  False, "reason": "NO_PROMOTION_FOUND"}, status_code = 400)
        await db.execute("DELETE FROM bot_promotions WHERE bot_id = $1 AND id = $2", id, promo.id)
    else:
        await db.execute("DELETE FROM bot_promotions WHERE bot_id = $1", id)
    return {"done":  True, "reason": None}


@router.patch("/bots/{bot_id}/token", response_model = APIResponse)
async def regenerate_token(request: Request, bot_id: int, Authorization: str = Header("INVALID_API_TOKEN")):
    """Regenerate the API token

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb
    """
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    await db.execute("UPDATE bots SET api_token = $1 WHERE bot_id = $2", get_token(132), id["bot_id"])
    return {"done": True, "reason": None}

@router.get("/bots/random", response_model = RandomBotsAPI)
async def random_bots_api(request: Request):
    random_unp = await db.fetchrow("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false AND banned = false AND disabled = false ORDER BY RANDOM() LIMIT 1") # Unprocessed
    bot = (await get_bot(random_unp["bot_id"])) | dict(random_unp)
    bot["bot_id"] = str(bot["bot_id"])
    bot["servers"] = human_format(bot["servers"])
    bot["description"] = bot["description"].replace("<", "").replace(">", "")
    return bot

@router.get("/bots/{bot_id}", response_model = Bot, dependencies=[Depends(RateLimiter(times=5, minutes=3))])
async def get_bots_api(request: Request, bot_id: int, Authorization: str = Header("INVALID_API_TOKEN")):
    """Gets bot information given a bot ID. If not found, 404 will be returned. If a proper API Token is provided, sensitive information (System API Events will also be provided)"""
    api_ret = await db.fetchrow("SELECT bot_id AS id, description, tags, html_long_description, long_description, servers AS server_count, shard_count, shards, prefix, invite, invite_amount, owner AS main_owner, extra_owners, features, bot_library AS library, queue, banned, certified, website, discord AS support, github, user_count, votes, css, donate FROM bots WHERE bot_id = $1", bot_id)
    if api_ret is None:
        return abort(404)
    api_ret = dict(api_ret)
    if api_ret["features"] is None:
        api_ret["features"] = []
    bot_obj = await get_bot(bot_id)
    if bot_obj is None:
        return abort(404)
    api_ret = api_ret | bot_obj
    api_ret["main_owner"] = str(api_ret["main_owner"])
    if api_ret["extra_owners"] is None:
        api_ret["extra_owners"] = []
    api_ret["extra_owners"] = [str(eo) for eo in api_ret["extra_owners"]]
    api_ret["owners"] = [api_ret["main_owner"]] + api_ret["extra_owners"]
    api_ret["id"] = str(api_ret["id"])
    if Authorization is not None:
        check = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", str(Authorization))
        if check is None or check["bot_id"] != bot_id:
            sensitive = False
        else:
            sensitive = True
    else:
        sensitive = False
    if sensitive:
        api_ret["sensitive"] = await get_events(bot_id = bot_id)
    else:
        api_ret["sensitive"] = {}
    vanity = await db.fetchrow("SELECT vanity_url FROM vanity WHERE redirect = $1", bot_id)
    if vanity is None:
        api_ret["vanity"] = None
    else:
        api_ret["vanity"] = vanity["vanity_url"]
    return api_ret

@router.get("/bots/{bot_id}/reviews", response_model = BotReviews)
async def get_bot_reviews(request: Request, bot_id: int):
    reviews = await parse_reviews(bot_id)
    if reviews[0] == []:
        return abort(404)
    return {"reviews": reviews[0], "average_stars": reviews[1]}

@router.get("/bots/{bot_id}/commands", response_model = BotCommands)
async def get_bot_commands_api(request:  Request, bot_id: int):
    cmd = await get_bot_commands(bot_id)
    if cmd == {}:
        return abort(404)
    return cmd

@router.post("/bots/{bot_id}/commands", response_model = BotCommandAddResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def add_bot_command_api(request: Request, bot_id: int, command: BotCommandAdd, Authorization: str = Header("INVALID_API_TOKEN"), force_add: Optional[bool] = False):
    """
        Self explaining command. Note that if force_add is set, the API will not check if your command already exists and will forcefully add it, this may lead to duplicate commands on your bot. If ret_id is not set, you will not get the command id back in the api response
    """
    if command.slash not in [0, 1, 2]:
        return ORJSONResponse({"done":  False, "reason": "UNSUPPORTED_MODE"}, status_code = 400)

    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)

    if force_add is False:
        check = await db.fetchrow("SELECT name FROM bot_commands WHERE name = $1 AND bot_id = $2", command.name, bot_id)
        if check is not None:
            return ORJSONResponse({"done":  False, "reason": "COMMAND_ALREADY_EXISTS"}, status_code = 400)
    id = uuid.uuid4()
    await db.execute("INSERT INTO bot_commands (id, bot_id, slash, name, description, args, examples, premium_only, notes, doc_link) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)", id, bot_id, command.slash, command.name, command.description, command.args, command.examples, command.premium_only, command.notes, command.doc_link)
    return {"done": True, "reason": None, "id": id}

@router.patch("/bots/{bot_id}/commands", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def edit_bot_command_api(request: Request, bot_id: int, command: BotCommandEdit, Authorization: str = Header("INVALID_API_TOKEN")):
    if command.slash not in [0, 1, 2]:
        return ORJSONResponse({"done":  False, "reason": "UNSUPPORTED_MODE"}, status_code = 400)

    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    data = await db.fetchrow(f"SELECT id, slash, name, description, args, examples, premium_only, notes, doc_link FROM bot_commands WHERE id = $1 AND bot_id = $2", command.id, bot_id)
    if data is None:
        return abort(404)

    # Check values to be editted
    command_dict = command.dict()
    for key in command_dict.keys():
        if command_dict[key] is None: 
            command_dict[key] = data[key]
    await db.execute("UPDATE bot_commands SET slash = $2, name = $3, description = $4, args = $5, examples = $6, premium_only = $7, notes = $8, doc_link = $9 WHERE id = $1", command_dict["id"], command_dict["slash"], command_dict["name"], command_dict["description"], command_dict["args"], command_dict["examples"], command_dict["premium_only"], command_dict["notes"], command_dict["doc_link"])
    return {"done": True, "reason": None}

@router.delete("/bots/{bot_id}/commands", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def delete_bot_command_api(request: Request, bot_id: int, command: BotCommandDelete, Authorization: str = Header("INVALID_API_TOKEN")):
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    await db.execute("DELETE FROM bot_commands WHERE id = $1 AND bot_id = $2", command.id, bot_id)
    return {"done": True, "reason": None}

@router.get("/bots/{bot_id}/votes", response_model = BotVoteCheck, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
async def get_votes_api(request: Request, bot_id: int, user_id: Optional[int] = None, Authorization: str = Header("INVALID_API_TOKEN")):
    """Endpoint to check amount of votes a user has."""
    if user_id is None:
        return dict((await db.fetchrow("SELECT votes FROM bots WHERE bot_id = $1", bot_id))) | {"vote_epoch": 0, "voted": False, "time_to_vote": 1, "vote_right_now": False}
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    voters = await db.fetchrow("SELECT timestamps FROM bot_voters WHERE bot_id = $1 AND user_id = $2", int(bot_id), int(user_id))
    if voters is None:
        return {"votes": 0, "voted": False, "vote_epoch": 0, "time_to_vote": 0, "vote_right_now": True}
    voter_count = len(voters["timestamps"])
    vote_epoch = await db.fetchrow("SELECT vote_epoch FROM users WHERE user_id = $1", user_id)
    if vote_epoch is None:
        vote_epoch = 0
    else:
        vote_epoch = vote_epoch["vote_epoch"]
    WT = 60*60*8 # Wait Time
    time_to_vote = WT - (time.time() - vote_epoch)
    if time_to_vote < 0:
        time_to_vote = 0
    return {"votes": voter_count, "voted": voter_count != 0, "vote_epoch": vote_epoch, "time_to_vote": time_to_vote, "vote_right_now": time_to_vote == 0}

@router.get("/bots/{bot_id}/votes/timestamped")
async def timestamped_get_votes_api(request: Request, bot_id: int, user_id: Optional[int] = None, Authorization: str = Header("INVALID_API_TOKEN")):
    """Endpoint to check amount of votes a user has with timestamps. This does not return whether a user can vote"""
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    elif user_id is not None:
        ldata = await db.fetch("SELECT userid, timestamps FROM bot_voters WHERE bot_id = $1 AND user_id = $2", int(bot_id), int(user_id))
    else:
        ldata = await db.fetch("SELECT userid, timestamps FROM bot_voters WHERE bot_id = $1", int(bot_id))
    ret = {}
    for data in ldata:
        ret[str(data["userid"])] = data["timestamps"]
    return {"user": "timestamp"} | ret

@router.post("/bots/{bot_id}/stats", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
async def set_bot_stats_api(request: Request, bt: BackgroundTasks, bot_id: int, api: BotStats, Authorization: str = Header("INVALID_API_TOKEN")):
    """
    This endpoint allows you to set the guild + shard counts for your bot
    """
    id = await db.fetchrow("SELECT bot_id, shard_count, shards, user_count FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
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
    bt.add_task(set_stats, bot_id = id["bot_id"], guild_count = api.guild_count, shard_count = shard_count, shards = shards, user_count = user_count)
    return {"done": True, "reason": None}

@router.get("/bots/{bot_id}/maintenance", response_model = BotMaintenance)
async def get_maintenance_mode(request: Request, bot_id: int):
    ret = await get_maint(bot_id = bot_id)
    if ret.get("fail"):
        return abort(404)
    return ret

@router.post("/bots/{bot_id}/maintenance", response_model = APIResponse)
async def set_maintenance_mode(request: Request, bot_id: int, api: BotMaintenancePartial, Authorization: str = Header("INVALID_API_TOKEN")):
    """This is just an endpoing for enabling or disabling maintenance mode. As of the new API Revamp, this is the only way to enable or disable maintenance mode as of right now

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token

    **Mode**: Whether you want to enter or exit maintenance mode. Setting this to 1 will enable maintenance, setting this to 2 will enable long-lasting maintenance mode and setting this to 0 will disable maintenance mode. More flying in soon :)
    """
    
    if api.mode not in [0, 1]:
        return ORJSONResponse({"done":  False, "reason": "UNSUPPORTED_MODE"}, status_code = 400)

    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    await add_maint(id["bot_id"], api.mode, api.reason)
    return {"done": True, "reason": None}

@router.get("/features/{name}")
async def get_feature_api(request: Request, name: str):
    """Gets a feature given its internal name (custom_prefix, open_source etc)"""
    if name not in features.keys():
        return abort(404)
    return features[name]

@router.get("/tags/{name}")
async def get_tags_api(request: Request, name: str):
    """Gets a tag given its internal name (custom_prefix, open_source etc)"""
    if name not in TAGS.keys():
        return abort(404)
    return {"name": name.replace("_", " ").title(), "iconify_data": TAGS[name], "id": name}

@router.get("/vanity/{vanity}", response_model = BotVanity)
async def get_vanity(request: Request, vanity: str):
    vb = await vanity_bot(vanity, compact = True)
    if vb is None:
        return abort(404)
    return {"type": vb[0], "redirect": vb[1]}

@router.get("/bots/ext/index")
async def bots_index_page_api(request: Request):
    """For any potential Android/iOS app, crawlers etc."""
    return await render_index(request = request, api = True)

@router.get("/bots/ext/search")
async def bots_search_page(request: Request, query: str):
    """For any potential Android/iOS app, crawlers etc. Query is the query to search for"""
    return await render_search(request = request, q = query, api = True)

@router.post("/preview", response_model = PrevResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def preview_api(request: Request, data: PrevRequest):
    if not data.html_long_description:
        html = emd(markdown.markdown(data.data, extensions=["extra", "abbr", "attr_list", "def_list", "fenced_code", "footnotes", "tables", "admonition", "codehilite", "meta", "nl2br", "sane_lists", "toc", "wikilinks", "smarty", "md_in_html"]))
    else:
        html = data.data
    # Take the h1...h5 anad drop it one lower
    html = html.replace("<h1", "<h2 style='text-align: center'").replace("<h2", "<h3").replace("<h4", "<h5").replace("<h6", "<p").replace("<a", "<a class='long-desc-link'").replace("ajax", "").replace("http://", "https://").replace(".alert", "")
    return {"html": html}


async def ws_close(websocket: WebSocket, code: int):
    try:
        return await websocket.close(code=code)
    except:
        return

@router.websocket("/api/v/2/ws") # Compatibility, will be undocumented soon
@router.websocket("/api/v/2/ws/bot")
async def websocket_bot(websocket: WebSocket):
    await manager.connect(websocket)
    if websocket.api_token == []:
        await manager.send_personal_message({"payload": "IDENTITY", "type": "API_TOKEN"}, websocket)
        try:
            api_token = await websocket.receive_json()
            print("HERE")
            if api_token.get("payload") != "IDENTITY_RESPONSE" or api_token.get("type") != "API_TOKEN":
                raise TypeError
        except:
            await manager.send_personal_message({"payload": "KILL_CONN", "type": "INVALID_IDENTITY_RESPONSE"}, websocket)
            return await ws_close(websocket, 4004)
        api_token = api_token.get("data")
        if api_token is None or type(api_token) == int or type(api_token) == str:
            await manager.send_personal_message({"payload": "KILL_CONN", "type": "INVALID_IDENTITY_RESPONSE"}, websocket)
            return await ws_close(websocket, 4004)
        for bot in api_token:
            bid = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", str(bot))
            if bid is None:
                pass
            else:
                websocket.api_token.append(api_token)
                websocket.bot_id.append(bid["bot_id"])
        if websocket.api_token == [] or websocket.bot_id == []:
            await manager.send_personal_message({"payload": "KILL_CONN", "type": "NO_AUTH"}, websocket)
            return await ws_close(websocket, 4004)
    await manager.send_personal_message({"payload": "STATUS", "type": "READY", "data": [str(bid) for bid in websocket.bot_id]}, websocket)
    try:
        ini_events = {}
        for bot in websocket.bot_id:
            events = await redis_db.hget(str(bot), key = "ws")
            if events is None:
                events = {} # Nothing
            else:
                try:
                    events = orjson.loads(events)
                except Exception as exc:
                    print(exc)
                    events = {}
            ini_events[str(bot)] = events
        await manager.send_personal_message({"payload": "EVENTS", "type": "EVENTS_V1", "data": ini_events}, websocket)
        pubsub = redis_db.pubsub()
        for bot in websocket.bot_id:
            await pubsub.subscribe(str(bot))
        async for msg in pubsub.listen():
            print(msg)
            if msg is None or type(msg.get("data")) != bytes:
                continue
            await manager.send_personal_message({"payload": "EVENTS", "type": "EVENTS_V1", "data": {msg.get("channel").decode("utf-8"): orjson.loads(msg.get("data"))}}, websocket)
    except:
        try:
            await pubsub.unsubscribe()
        except:
            pass
        await manager.disconnect(websocket)

# Chat

@router.websocket("/api/ws/v/2/chat")
async def chat_api(websocket: WebSocket):
    await manager_chat.connect(websocket)
    if not websocket.authorized:
        await manager_chat.send_personal_message({"payload": "IDENTITY", "type": "USER|BOT"}, websocket)
        try:
            identity = await websocket.receive_json()
            print("HERE")
            if identity.get("payload") != "IDENTITY_RESPONSE":
                raise TypeError
        except:
            await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "INVALID_IDENTITY_RESPONSE"}, websocket)
            return await ws_close(websocket, 4004)
        data = identity.get("data")
        if data is None or type(data) != str:
            await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "NO_AUTH"}, websocket) # Invalid api token provided
            return await ws_close(websocket, 4004)
        match identity.get("type"):
            case "USER":
                acc_type = 0
                sender = await db.fetchval("SELECT user_id FROM users WHERE api_token = $1", identity.get("data"))
            case "BOT":
                acc_type = 1
                sender = await db.fetchval("SELECT bot_id FROM bots WHERE api_token = $1", identity.get("data"))
            case _:
                await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "NOT_IMPLEMENTED"}, websocket)
                return await ws_close(websocket, 4005) # 4005 = Not Implemented
        if sender is None:
            await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "NO_AUTH"}, websocket) # Invalid api token provided
            return await ws_close(websocket, 4004)
    websocket.authorized = True
    await manager_chat.send_personal_message({"payload": "CHAT_USER", "type": "CHAT", "data": (await get_any(sender))}, websocket)    
    try:
        await redis_db.incrbyfloat(str(sender) + "_cli_count")
        messages = await redis_db.hget("global_chat", key = "message")
        if messages is None:
            messages = b"" # No messages
        await manager_chat.send_personal_message({"payload": "MESSAGE", "type": "BULK", "data": messages.decode("utf-8")}, websocket) # Send all messages in bulk
        pubsub = redis_db.pubsub()
        await pubsub.subscribe("global_chat_channel")
        async for msg in pubsub.listen():
            print("Got msg")
            if type(msg['data']) != bytes:
                continue
            try:
                msg_info = orjson.loads(msg['data'].decode('utf-8'))
            except:
                continue
            await manager_chat.send_personal_message(msg_info, websocket) # Send all messages in bulk
    except Exception as e:
        await redis_db.decrby(str(sender) + "_cli_count")
        print(e)
        await pubsub.unsubscribe()
        await manager_chat.disconnect(websocket)

async def chat_publish_message(msg):
    pass

# End Chat

@router.get("/users/{user_id}", response_model = User)
async def get_user_api(request: Request, user_id: int):
    user = await db.fetchrow("SELECT description, css FROM users WHERE user_id = $1", user_id)
    if user is None:
        return abort(404)
    user_obj = await get_user(user_id)
    user_ret = dict(user) | user_obj
    return user_ret

@router.get("/users/{user_id}/valid_servers", tags = ["API (Internal)"], dependencies=[Depends(RateLimiter(times=3, minutes=5))], response_model = ValidServer, include_in_schema = False)
async def get_valid_servers_api(request: Request, user_id: int):
    """Internal API to get users who have the FL Server Bot and Manage Server/Admin"""
    valid = {}
    if "dscopes_str" not in request.session.keys():
        return abort(400)
    access_token = await discord_o.access_token_check(request.session["dscopes_str"], request.session["access_token"])
    request.session["access_token"] = access_token
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
            print(guild.id)
            guild_json = {"icon": str(guild.icon_url), "name": guild.name, "member_count": guild.member_count, "created_at": str(guild.created_at.timestamp()), "code": get_token(37)}
            await redis_db.hset(str(guild.id), key = "cache", value = orjson.dumps(guild_json))
            valid = valid | {str(guild.id): guild_json}
    print(valid)
    return {"valid": valid}

@router.patch("/users/{user_id}/description")
async def set_user_description_api(request: Request, user_id: int, desc: UserDescEdit, Authorization: str = Header("INVALID_API_TOKEN")):
    id = await db.fetchrow("SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", user_id, str(Authorization))
    if id is None:
        return abort(401)
    await db.execute("UPDATE users SET description = $1 WHERE user_id = $2", desc.description, user_id)
    return {"done": True, "reason": None}


# Generic methods to add coins

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
    print("DM Customer: " + str(session))

