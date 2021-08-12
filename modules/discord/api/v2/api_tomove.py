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
async def get_bot_events_api(request: Request, bot_id: int, exclude: Optional[str] = None, filter: Optional[str] = None):
    """Get bot events, all exclude and filters must be comma seperated"""
    exclude = exclude.split(",")
    filter = filter.split(",")
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

@router.get(
    "/bots/{bot_id}/commands", 
    response_model = BotCommandsGet
)
async def get_commands(request:  Request, bot_id: int, filter: Optional[str] = None, lang: str = "default"):
    cmd = await get_bot_commands(bot_id, lang, filter)
    if cmd == {}:
        return abort(404)
    return cmd

@router.post(
    "/bots/{bot_id}/commands",
    response_model = IDResponse, 
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
async def add_command(request: Request, bot_id: int, command: BotCommand):
    """
    Adds a command to your bot. If it already exists, this will delete and readd the command so it can be used to edit already existing commands
    """
    check = await db.fetchval("SELECT COUNT(1) FROM bot_commands WHERE cmd_name = $1 AND bot_id = $2", command.cmd_name, bot_id)
    if check:
        await db.execute("DELETE FROM bot_commands WHERE cmd_name = $1 AND bot_id = $2", command.cmd_name, bot_id)
    id = uuid.uuid4()
    await db.execute("INSERT INTO bot_commands (id, bot_id, cmd_groups, cmd_type, cmd_name, description, args, examples, premium_only, notes, doc_link, vote_locked) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)", id, bot_id, command.cmd_groups, command.cmd_type, command.cmd_name, command.description, command.args, command.examples, command.premium_only, command.notes, command.doc_link, command.vote_locked)
    await bot_add_event(bot_id, enums.APIEvents.command_add, {"user": None, "id": id})
    return api_success(id = id)

@router.delete(
    "/bots/{bot_id}/commands/{id}", 
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
async def delete_command(request: Request, bot_id: int, id: uuid.UUID):
    cmd = await db.fetchval("SELECT id FROM bot_commands WHERE id = $1 AND bot_id = $2", id, bot_id)
    if not cmd:
        return abort(404)
    await db.execute("DELETE FROM bot_commands WHERE id = $1 AND bot_id = $2", id, bot_id)
    await bot_add_event(bot_id, enums.APIEvents.command_delete, {"user": None, "id": id})
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


@router.get(
    "/users/{user_id}"
)
async def get_user_api(request: Request, user_id: int, worker_session = Depends(worker_session)):
    user = await core.User(id = user_id, db = worker_session.postgres, client = worker_session.discord.main).profile()
    if not user:
        return abort(404)
    return user

# guilds = await discord_o.get_guilds(access_token["access_token"], permissions = [0x8, 0x20]) # Check for admin/manage server in future

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

