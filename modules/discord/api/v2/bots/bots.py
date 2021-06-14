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
    return api_success()

@router.get("/bots/random", response_model = BotRandom, dependencies=[Depends(RateLimiter(times=7, seconds=5))])
async def random_bots_api(request: Request, lang: str = "default"):
    random_unp = await db.fetchrow("SELECT description, banner, state, votes, servers, bot_id, invite FROM bots WHERE state = 0 OR state = 6 ORDER BY RANDOM() LIMIT 1") # Unprocessed, use the random function to get a random bot
    try:
        bot = (await get_bot(random_unp["bot_id"])) | dict(random_unp) # Get bot from cache and add that in
    except:
        return await random_bots_api(request) 
    bot["bot_id"] = str(bot["bot_id"]) # Make sure bot id is a string to prevent corruption issues
    bot["servers"] = human_format(bot["servers"]) # Format the servers field
    bot["description"] = cleaner.clean_html(intl_text(bot["description"], lang)) # Prevent some basic attacks in short description
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
