"""Modules to move"""
from typing import Dict, List
from uuid import UUID

from fastapi.responses import HTMLResponse

from modules.core import *
from modules.discord.api.v2.modelstomove import *  # TODO

API_VERSION = 2 # This is the API version

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - To Move"]
)

@router.get(
    "/bots/{bot_id}/events", 
    response_model = BotEvents,
    dependencies = [
        Depends(bot_auth_check)
    ]
)
async def get_bot_events_api(request: Request, bot_id: int, exclude: Optional[list] = None, filter: Optional[list] = None):
    return await bot_get_events(bot_id = bot_id, filter = filter, exclude = exclude)

@router.get(
    "/bots/{bot_id}/ws_events",
    dependencies = [
        Depends(bot_auth_check)
    ]
)
async def get_bot_ws_events(request: Request, bot_id: int):
    ini_events = {}
    events = await redis_db.hget(f"{type}-{bot_id}", key = "ws")
    if events is None:
        events = {} # Nothing
    return events

@router.get(
    "/bots/{bot_id}/reviews", 
    response_model = BotReviews
)
async def get_bot_reviews(request: Request, bot_id: int, page: Optional[int] = 1):
    reviews = await parse_reviews(bot_id, page = page)
    if reviews[0] == []:
        return abort(404)
    return {"reviews": reviews[0], "average_stars": reviews[1], "pager": {"total_count": reviews[2], "total_pages": reviews[3], "per_page": reviews[4], "from": ((page - 1) * reviews[4]) + 1, "to": (page - 1) * reviews[4] + len(reviews[0])}}

@router.patch(
    "/bots/{bot_id}/reviews/{rid}/votes", 
    response_model = APIResponse,
    dependencies = [
        Depends(user_auth_check)
    ]
)
async def vote_review_api(request: Request, bot_id: int, rid: uuid.UUID, vote: BotReviewVote):
    vote.user_id = int(vote.user_id)
    bot_rev = await db.fetchrow("SELECT review_upvotes, review_downvotes, star_rating, reply, review_text FROM bot_reviews WHERE id = $1", rid)
    if bot_rev is None:
        return api_error("You are not allowed to up/downvote this review (doesn't actually exist)", 3836)
    bot_rev = dict(bot_rev)
    if vote.upvote:
        main_key = "review_upvotes"
        remove_key = "review_downvotes"
    else:
        main_key = "review_downvotes"
        remove_key = "review_upvotes"
    if vote.user_id in bot_rev[main_key]:
        return api_error("The user has already voted for this review", 5858)
    if vote.user_id in bot_rev[remove_key]:
        while True:
            try:
                bot_rev[remove_key].remove(vote.user_id)
            except:
                break
    bot_rev[main_key].append(vote.user_id)
    await db.execute("UPDATE bot_reviews SET review_upvotes = $1, review_downvotes = $2 WHERE id = $3", bot_rev["review_upvotes"], bot_rev["review_downvotes"], rid)
    await bot_add_event(bot_id, enums.APIEvents.review_vote, {"user": str(vote.user_id), "id": str(rid), "star_rating": bot_rev["star_rating"], "reply": bot_rev["reply"], "review": bot_rev["review_text"], "upvotes": len(bot_rev["review_upvotes"]), "downvotes": len(bot_rev["review_downvotes"]), "upvote": vote.upvote})
    return api_success()

@router.delete(
    "/bots/{bot_id}/reviews/{rid}", 
    response_model = APIResponse
)
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
            return api_error("You are not allowed to delete this review", 1232)
    else:
        check = await db.fetchrow("SELECT replies FROM bot_reviews WHERE id = $1 AND bot_id = $2 AND user_id = $3", rid, bot_id, data.user_id)
        if check is None:
            return api_error("You are not allowed to delete this review", 1232)
    event_data = await db.fetchrow("SELECT reply, review_text, star_rating FROM bot_reviews WHERE id = $1", rid) # Information needed to send an event
    await db.execute("DELETE FROM bot_reviews WHERE id = $1", rid)
    await bot_add_event(bot_id, enums.APIEvents.review_delete, {"user": str(data.user_id), "reply": event_data["reply"], "id": str(rid), "star_rating": event_data["star_rating"], "review": event_data["review_text"]})
    return api_success()

@router.get(
    "/bots/{bot_id}/commands", 
    response_model = BotCommandsGet
)
async def get_bot_commands_api(request:  Request, bot_id: int, filter: Optional[str] = None, lang: str = "default"):
    cmd = await get_bot_commands(bot_id, lang, filter)
    if cmd == {}:
        return abort(404)
    return cmd

@router.post(
    "/bots/{bot_id}/commands",
    response_model = BotCommandAddResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        ),
        Depends(bot_auth_check)
    ]
)
async def add_bot_command_api(request: Request, bot_id: int, command: PartialBotCommand, force_add: Optional[bool] = False):
    """
        Self explaining command. Note that if force_add is set, the API will not check if your command already exists and will forcefully add it, this may lead to duplicate commands on your bot. If ret_id is not set, you will not get the command id back in the api response
    """
    if force_add is False:
        check = await db.fetchval("SELECT COUNT(1) FROM bot_commands WHERE cmd_name = $1 AND bot_id = $2", command.cmd_name, bot_id)
        if check:
            return api_error("A command with this name already exists on your bot", 6858)
    id = uuid.uuid4()
    await db.execute("INSERT INTO bot_commands (id, bot_id, cmd_groups, cmd_type, cmd_name, description, args, examples, premium_only, notes, doc_link, friendly_name) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)", id, bot_id, command.cmd_groups, command.cmd_type, command.cmd_name, command.description, command.args, command.examples, command.premium_only, command.notes, command.doc_link, command.friendly_name)
    await bot_add_event(bot_id, enums.APIEvents.command_add, {"user": None, "id": id})
    return api_success(id = id)

@router.patch(
    "/bots/{bot_id}/commands", 
    response_model = APIResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        ), 
        Depends(bot_auth_check)
    ]
)
async def edit_bot_command_api(request: Request, bot_id: int, command: BotCommand):
    data = await db.fetchrow(f"SELECT id, cmd_type, cmd_groups, cmd_name, friendly_name, description, args, examples, premium_only, notes, doc_link FROM bot_commands WHERE id = $1 AND bot_id = $2", command.id, bot_id)
    if data is None:
        return abort(404)

    # Check values to be editted
    command_dict = command.dict()
    for key in command_dict.keys():
        if command_dict[key] is None: 
            command_dict[key] = data[key]
    await db.execute("UPDATE bot_commands SET cmd_type = $2, cmd_name = $3, description = $4, args = $5, examples = $6, premium_only = $7, notes = $8, doc_link = $9, cmd_groups = $10, friendly_name = $11 WHERE id = $1", command_dict["id"], command_dict["cmd_type"], command_dict["cmd_name"], command_dict["description"], command_dict["args"], command_dict["examples"], command_dict["premium_only"], command_dict["notes"], command_dict["doc_link"], command_dict["cmd_groups"], command_dict["friendly_name"])
    await bot_add_event(bot_id, enums.APIEvents.command_edit, {"user": None, "id": command.id})
    return api_success()

@router.delete(
    "/bots/{bot_id}/commands", 
    response_model = APIResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        ), 
        Depends(bot_auth_check)
    ]
)
async def delete_bot_command_api_(request: Request, bot_id: int, command: BotCommandDelete):
    if command.id:
        cmd = await db.fetchval("SELECT id FROM bot_commands WHERE id = $1 AND bot_id = $2", command.id, bot_id)
    elif command.cmd_name:
        cmd = await db.fetchval("SELECT id FROM bot_commands WHERE cmd_name = $1 AND bot_id = $2", command.cmd_name, bot_id)
    if not cmd:
        return abort(404)
    if command.id:
        await db.execute("DELETE FROM bot_commands WHERE id = $1 AND bot_id = $2", command.id, bot_id)
    elif command.cmd_name:
        await db.execute("DELETE FROM bot_commands WHERE cmd_name = $1 AND bot_id = $2", command.cmd_name, bot_id)
    await bot_add_event(bot_id, enums.APIEvents.command_delete, {"user": None, "id": command.id})
    return api_success()

@router.get(
    "/bots/{bot_id}/maintenance", 
    response_model = BotMaintenance
)
async def get_maintenance_mode(request: Request, bot_id: int):
    ret = await get_maint(bot_id = bot_id)
    if ret.get("fail"):
        return abort(404)
    return ret

@router.patch(
    "/bots/{bot_id}/maintenance", 
    response_model = APIResponse,
    dependencies = [
        Depends(bot_auth_check)
    ]
)
async def set_maintenance_mode(request: Request, bot_id: int, api: BotMaintenancePartial):
    """This is just an endpoint for enabling or disabling maintenance mode.

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token

    **Mode**: Whether you want to enter or exit maintenance mode. Setting this to 1 will enable maintenance, setting this to 2 will enable long-lasting maintenance mode and setting this to 0 will disable maintenance mode. More flying in soon :)
    """
    
    if api.mode not in [0, 1]:
        return api_error("The mode you are using is invalid", 36281)

    await add_maint(bot_id, api.mode, api.reason)
    return api_success()

@router.get(
    "/features/{name}", 
    response_model = FLFeature
)
async def get_feature_api(request: Request, name: str):
    """Gets a feature given its internal name (custom_prefix, open_source etc)"""
    if name not in features.keys():
        return abort(404)
    return features[name]

@router.get(
    "/tags/{name}", 
    response_model = FLTag
)
async def get_tags_api(request: Request, name: str):
    """Gets a tag given its internal name (custom_prefix, open_source etc)"""
    if name not in TAGS.keys():
        return abort(404)
    return {"name": name.replace("_", " ").title(), "iconify_data": TAGS[name], "id": name}

@router.get(
    "/code/{vanity}", 
    response_model = BotVanity
)
async def get_vanity_api(request: Request, vanity: str):
    vb = await vanity_bot(vanity)
    logger.trace(f"Vanity is {vanity} and vb is {vb}")
    if vb is None:
        return abort(404)
    return {"type": vb[1], "redirect": str(vb[0])}

@router.get(
    "/index/bots", 
    response_model = BotIndex
)
async def bots_index_page(request: Request):
    """For any potential Android/iOS app, crawlers etc."""
    return await render_index(request = request, api = True)

@router.get(
    "/search/bots", 
    response_model = BotSearch
)
async def bots_search_page(request: Request, q: str):
    """For any potential Android/iOS app, crawlers etc. Q is the query to search for"""
    return await render_search(request = request, q = q, api = True)

@router.get(
    "/search/profiles", 
    response_model = ProfileSearch,
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        )
    ]
)
async def profiles_search_page(request: Request, q: str):
    """For any potential Android/iOS app, crawlers etc. Q is the query to search for"""
    return await render_profile_search(request = request, q = q, api = True)

@router.post(
    "/preview", 
    response_model = PrevResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        )
    ]
)
async def preview_api(request: Request, data: PrevRequest, lang: str = "default"):
    if not data.html_long_description:
        html = emd(markdown.markdown(intl_text(data.data, lang), extensions=["extra", "abbr", "attr_list", "def_list", "fenced_code", "footnotes", "tables", "admonition", "codehilite", "meta", "nl2br", "sane_lists", "toc", "wikilinks", "smarty", "md_in_html"]))
    else:
        html = intl_text(data.data, lang)
    # Take the h1...h5 anad drop it one lower
    html = html.replace("<h1", "<h2 style='text-align: center'").replace("<h2", "<h3").replace("<h4", "<h5").replace("<h6", "<p").replace("<a", "<a class='long-desc-link'").replace("ajax", "").replace("http://", "https://").replace(".alert", "")
    return {"html": html}

# TODO: Properly document the actual API
@router.get(
    "/users/{user_id}"
)
async def get_user_api(request: Request, user_id: int, worker_session = Depends(worker_session)):
    user = await core.User(id = user_id, db = worker_session.postgres, client = worker_session.discord.main).profile()
    if not user:
        return abort(404)
    return user

@router.patch(
    "/users/{user_id}/bots/{bot_id}/reminders",
    dependencies = [
        Depends(user_auth_check)
    ]
)
async def set_vote_reminder(request: Request, user_id: int, bot_id: int, data: VoteReminderPatch):
    if data.remind:
        check = await db.fetchval("SELECT DISTINCT bot_id FROM user_reminders WHERE user_id = $1 AND bot_id = $2", user_id, bot_id)
        if check == 0:
            await db.execute("INSERT INTO user_reminders (user_id, bot_id) VALUES ($1, $2)", user_id, bot_id)
            return api_success()
        else:
            return api_error("User already signed up for vote reminders", 37373)
    else:
        await db.execute("DELETE FROM user_reminders WHERE user_id = $1 AND bot_id = $2", user_id, bot_id)
        return api_success()

@router.post(
    "/users/{user_id}/servers/prepare",
    response_model = ServerListAuthed,
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=3, seconds=35)
            )
        ),
        Depends(user_auth_check)
    ]
)
async def prepare_servers_api(request: Request, user_id: int, data: ServerCheck):
    """
    Prepares a user to add servers and returns available servers for said user. Scopes must have guild permission

    This request may change the access token and this should be set on the client and will be returned in the json response as well
    """
    return abort(503)
    valid = {}
    access_token = await discord_o.access_token_check(data.scopes, data.access_token.dict())
    request.session["access_token"] = access_token
    access_token["current_time"] = str(access_token["current_time"])
    guilds = await discord_o.get_guilds(access_token["access_token"], permissions = [0x8, 0x20]) # Check for all guilds with 0x8 and 0x20
    for guild in guilds:
        if (isinstance(guild, str) and guild.isdigit()) or isinstance(guild, int):
            guild_obj = client_servers.get_guild(int(server))
            if guild_obj is None:
                continue
        else:
            continue
       
        member = guild.get_member(user_id)
        if member is None:
            continue
            
        if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
            logger.debug(f"Adding {guild.id} to prepared server list")
            guild_json = {
                "icon": str(guild.icon_url),
                "name": guild.name, 
                "member_count": guild.member_count,
                "created_at": str(guild.created_at.timestamp()), 
                "code": get_token(37)
            }
            await redis_db.hset(str(guild.id), key = "cache", value = orjson.dumps(guild_json))
            valid = valid | {str(guild.id): guild_json}
    logger.debug(f"Valid servers are {valid}")
    return {"servers": valid, "access_token": access_token}

@router.post(
    "/servers/{guild_id}",
    dependencies=[
        Depends(user_auth_check)
    ]
)
async def add_guild_api(request: Request, guild_id: int, user_id: int, data: ServersAdd):
    guild_data = await redis_db.hget(str(guild_id), key = "cache")
    if guild_data is None:
        logger.trace(f"Guild data is {guild_data}")
        return abort(404)
    guild_data = orjson.loads(guild_data)
    if guild_data["code"] != data.code:
        return api_error("Bad code provided")
    server_actions = ServerActions(data.dict() | {"data": guild_data, "guild_id": guild_id, "user_id": user_id})
    rc = await server_actions.add_server()
    if rc is None:
        return api_success()
    return api_error(rc[0], rc[1])

@router.patch(
    "/users/{user_id}/description", 
    response_model = APIResponse,
    dependencies = [
        Depends(user_auth_check)
    ]
)
async def set_user_description_api(request: Request, user_id: int, desc: UserDescEdit):
    await db.execute("UPDATE users SET description = $1 WHERE user_id = $2", desc.description, user_id)
    return api_success()

@router.patch(
    "/users/{user_id}/token", 
    response_model = APIResponse,
    dependencies = [
        Depends(user_auth_check)
    ]
)
async def regenerate_user_token(request: Request, user_id: int):
    """Regenerate the User API token

    ** User API Token**: You can get this by clicking your profile and scrolling to the bottom and you will see your API Token
    """
    await db.execute("UPDATE users SET api_token = $1 WHERE user_id = $2", get_token(132), user_id)
    return api_success()

@router.patch(
    "/users/{user_id}/js_allowed",
    dependencies = [
        Depends(user_auth_check)
    ]
)
async def set_js_mode(request: Request, user_id: int, data: UserJSPatch):
    await db.execute("UPDATE users SET js_allowed = $1", data.js_allowed)
    request.session["js_allowed"] = data.js_allowed
    return api_success()

