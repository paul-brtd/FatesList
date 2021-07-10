from lxml.html.clean import Cleaner

from modules.core import *

from ..base import API_VERSION
from .models import APIResponse, Bot, BotRandom, BotStats

cleaner = Cleaner(remove_unknown_tags=False)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/bots",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Bots"]
)

@router.get(
    "/bots/{bot_id}/token",
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            )    
        ), 
        Depends(user_auth_check)
    ]
)
async def get_bot_token(request: Request, bot_id: int, user_id: int):
    """
    Gets a bot token given a user token. 401 = Invalid API Token, 403 = Forbidden (not owner of bot or staff)
    """
    bot_admin = await is_bot_admin(bot_id, user_id)
    if not bot_admin:
        return abort(403)
    return await db.fetchrow("SELECT api_token FROM bots WHERE bot_id = $1", bot_id)

@router.patch(
    "/{bot_id}/token", 
    response_model = APIResponse, 
    dependencies = [
        Depends(
            Ratelimiter(
                global_limit = Limit(times=7, minutes=3)
            )
        ), 
        Depends(bot_auth_check)
    ]
)
async def regenerate_bot_token(request: Request, bot_id: int):
    """
    Regenerates the Bot token
    **Bot Token**: You can get this by clicking your bot and clicking edit and clicking Show (under API Token section)
    """
    await db.execute("UPDATE bots SET api_token = $1 WHERE bot_id = $2", get_token(132), bot_id)
    return api_success()

@router.get(
    "/random", 
    response_model = BotRandom, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=7, seconds=5)
            )
        )
    ]
)
async def fetch_random_bot(request: Request, lang: str = "default"):
    random_unp = await db.fetchrow(
        "SELECT description, banner, state, votes, servers, bot_id, invite FROM bots WHERE state = 0 OR state = 6 ORDER BY RANDOM() LIMIT 1"
    ) # Unprocessed, use the random function to get a random bot
    bot_obj = await get_bot(random_unp["bot_id"], worker_session = request.app.state.worker_session)
    if bot_obj is None:
        return await fetch_random_bot(request, lang) # Get a new bot
    bot = bot_obj | dict(random_unp) # Get bot from cache and add that in
    bot["bot_id"] = str(bot["bot_id"]) # Make sure bot id is a string to prevent corruption issues in javascript
    bot["servers"] = human_format(bot["servers"]) # Format the servers field
    bot["description"] = cleaner.clean_html(intl_text(bot["description"], lang)) # Prevent XSS attacks in short description
    if bot["banner"] is None: # Ensure banner is always a string
        bot["banner"] = "" 
    return bot

@router.get(
    "/{bot_id}", 
    response_model = Bot, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=2)
            )
        )
    ]
)
async def fetch_bot(request: Request, bot_id: int):
    """Fetches bot information given a bot ID. If not found, 404 will be returned."""
    api_ret = await db.fetchrow(
        "SELECT banner, description, long_description_type, long_description, servers AS server_count, shard_count, shards, prefix, invite, invite_amount, features, bot_library AS library, state, website, discord AS support, github, user_count, votes, css, donate, privacy_policy, nsfw FROM bots WHERE bot_id = $1", 
        bot_id
    )
    if api_ret is None:
        return abort(404)
    api_ret = dict(api_ret)
    tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
    api_ret["tags"] = [tag["tag"] for tag in tags]
    owners_db = await db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", bot_id)
    owners = []
    _done = []

    # Preperly sort owners
    for owner in owners_db:
        if owner in _done: continue
        
        _done.append(owner["owner"])
        user = await get_user(owner["owner"])
        main = owner["main"]

        if not user: continue
        
        owner_obj = {
            "user": user,
            "main": main
        }
        
        if main: owners.insert(0, owner_obj)
        else: owners.append(owner_obj)

    api_ret["owners"] = owners
    if api_ret["features"] is None:
        api_ret["features"] = []
    api_ret["invite_link"] = await invite_bot(bot_id, api = True)
    bot_obj = await get_bot(bot_id)
    if bot_obj is None:
        return abort(404)
    api_ret = api_ret | bot_obj
    api_ret["vanity"] = await db.fetchval(
        "SELECT vanity_url FROM vanity WHERE redirect = $1", 
        bot_id
    )
    return api_ret

@router.get(
    "/{bot_id}/widget",
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=2)
            )
        )
    ]
)
async def get_bot_widget(request: Request, bot_id: int, bt: BackgroundTasks):
    return await render_bot_widget(request, bt, bot_id, api = True)

@router.get(
    "/{bot_id}/raw",
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=4)
            )
        )
    ]
)
async def get_raw_bot(request: Request, bot_id: int, bt: BackgroundTasks):
    """
    Gets the raw given to the template with a few differences (bot_id being string and not int and passing auth manually to the function (coming soon) as the API aims to be as stateless as possible)
    Note that you likely want the Get Bot API and not this in most cases
    This API is prone to change as render_bot will keep changing
    """
    return await render_bot(request, bt, bot_id, api = True)

@router.post(
    "/{bot_id}/stats", 
    response_model = APIResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            ) 
        ),
        Depends(bot_auth_check)
    ]
)
async def set_bot_stats(request: Request, bot_id: int, api: BotStats):
    """This endpoint allows you to set the guild + shard counts for your bot"""
    stats_old = await db.fetchrow(
        "SELECT servers AS guild_count, shard_count, shards, user_count FROM bots WHERE bot_id = $1",
        bot_id
    )
    stats_new = api.dict()
    stats = {}
    for stat in stats_new.keys():
        if stats_new[stat] is None:
            stats[stat] = stats_old[stat]
        else:
            stats[stat] = stats_new[stat]
    await set_stats(bot_id = bot_id, **stats)
    return api_success()
