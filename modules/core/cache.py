from .imports import *

async def _user_fetch(user_id: str, user_type: int, user_only: bool = False) -> Optional[dict]:
    # Check if a suitable version is in the cache first before querying Discord

    CACHE_VER = 10 # Current cache ver

    if len(user_id) not in [17, 18, 19, 20]: # Snowflake can be 17 - 21
        print("Ignoring blatantly wrong User ID")
        return None # This is impossible to actually exist on the discord API or on our cache

    # Query redis cache for some important info
    cache_redis = await redis_db.hget(str(user_id), key = 'cache') # This is bot in cache
    if cache_redis is not None: # We got a match
        cache = orjson.loads(cache_redis) # Make it JSON
        cache_time = time.time() - cache['epoch']
        if cache.get("fl_cache_ver") != CACHE_VER or (cache.get("valid_user") is None and time.time() - cache_time > 60*10) or cache_time > 60*60*8: # Check for cache expiry of 8 hours for proper user, 10 minutes for invalid, proper cache version and that its a valid user
            # The cache is invalid, pass and make discord api call
            print("Not using cache for id ", user_id)
            pass
        else:
            print("Using cache for id ", user_id) # Use cache
            fetch = False
            if cache.get("valid_user") and ((user_type == 2 and cache["bot"]) or user_type == 3): # Valid user and bot where bot is requested or all users requested
                fetch = True
            elif cache.get("valid_user") and user_type == 1 and not cache["bot"]: # Valid users and user where user is requested or all users requested
                fetch = True
            if fetch: # We got a match
                if user_only:
                    return user_id, cache["username"]
                return {"id": user_id, "username": cache['username'], "avatar": cache['avatar'], "disc": cache["disc"], "status": cache["status"], "bot": cache["bot"]}
            return None # We got a bot, but not fitting in constraints

    # Add ourselves to cache
    valid_user = False # Flag for valid user
    bot = False # Flag for bot
    username, avatar, disc = None, None, None # All are none at first

    try:
        print(f"Making API call to get user {user_id}")
        bot_obj = await client.fetch_user(int(user_id)) # Use fetch user to actually use HTTP api and not cache to allow bots not in guild
        valid_user = True # It worked and didn't error, set valid_user
        bot = bot_obj.bot # Set bot flag accordingly
    except Exception as ex:
        valid_user, bot = False, False # Not a proper got, cache to avoid repitition
        print(ex)

    try:
        status = str(client.get_guild(main_server).get_member(int(user_id)).status) # Get the status by getting guild, getting member and then setting status, may fail if not in guild so catch that using try except above
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
        print("Setting db username to " + username + " for " + str(user_id))
        try:
            await db.execute("UPDATE bots SET username_cached = $2 WHERE bot_id = $1", int(user_id), username)
        except:
            pass # Sometimes this cannot be done

    cache = orjson.dumps({"fl_cache_ver": CACHE_VER, "epoch": time.time(), "bot": bot, "username": username, "avatar": avatar, "disc": disc, "valid_user": valid_user, "status": status}) # Create cache and dump it to string for caching
    await redis_db.hset(str(user_id), key = "cache", value = cache) # Add/Update redis

    fetch = False
    if valid_user and ((user_type == 2 and bot) or user_type == 3): # Same as when cached, see that for this
        fetch = True
    elif user_type == 1 and valid_user and not bot:
        fetch = True
    if fetch:
        if user_only:
            return user_id, username
        return {"id": user_id, "username": username, "avatar": avatar, "disc": disc, "status": status, "bot": bot}
    return None

async def get_user(user_id: int, user_only = False) -> Optional[dict]:
    return await _user_fetch(str(int(user_id)), 1, user_only = user_only) # 1 means user

async def get_bot(user_id: int, user_only = False) -> Optional[dict]:
    return await _user_fetch(str(int(user_id)), 2, user_only = user_only) # 2 means bot

async def get_any(user_id: int, user_only = False) -> Optional[dict]:
    return await _user_fetch(str(int(user_id)), 3, user_only = user_only) # 3 means all
