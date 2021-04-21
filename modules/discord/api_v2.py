from ..core import *
from uuid import UUID
from fastapi.responses import HTMLResponse
from typing import List, Dict
from modules.models.api_v2 import *
from modules.models.bot_actions import BotAdd, BotEdit

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

@router.post("/bots/{bot_id}/promotions", response_model = APIResponse, responses = {
    400: {"model": APIResponse}
})
async def add_promotion_api(request: Request, bot_id: int, promo: BotPromotionPartial, Authorization: str = Header("BOT_TOKEN")):
    """Creates a promotion for a bot. Type can be 1 for announcement, 2 for promotion or 3 for generic

    """
    if len(promo.title) < 3:
        return ORJSONResponse({"done":  False, "reason": "TEXT_TOO_SMALL", "code": 9898}, status_code = 400)
    if promo.type not in [1, 2, 3]:
        return ORJSONResponse({"done":  False, "reason": "INVALID_PROMO_TYPE", "code": 9897}, status_code = 400)
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    id = id["bot_id"]
    await add_promotion(id, promo.title, promo.info, promo.css, promo.type)
    return {"done":  True, "reason": None, "code": 1000}

@router.patch("/bots/{bot_id}/promotions", response_model = APIResponse, responses = {
    400: {"model": APIResponse}
})
async def edit_promotion(request: Request, bot_id: int, promo: BotPromotion, Authorization: str = Header("BOT_TOKEN")):
    """Edits an promotion for a bot given its promotion ID.

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Promotion ID**: This is the ID of the promotion you wish to edit 

    """
    if len(promo.title) < 3:
        return ORJSONResponse({"done":  False, "reason": "TEXT_TOO_SMALL", "code": 2919}, status_code = 400)
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    pid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1 AND bot_id = $2", promo.id, bot_id)
    if pid is None:
        return ORJSONResponse({"done":  False, "reason": "NO_PROMOTION_FOUND", "code": 2917}, status_code = 400)
    await db.execute("UPDATE bot_promotions SET title = $1, info = $2 WHERE bot_id = $3 AND id = $4", promo.title, promo.info, bot_id, promo.id)
    return {"done": True, "reason": None, "code": 1000}

@router.delete("/bots/{bot_id}/promotions", response_model = APIResponse, responses = {
    400: {"model": APIResponse}
})
async def delete_promotion(request: Request, bot_id: int, promo: BotPromotionDelete, Authorization: str = Header("BOT_TOKEN")):
    """Deletes a promotion for a bot or deletes all promotions from a bot

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Event ID**: This is the ID of the event you wish to delete. Not passing this will delete ALL events, so be careful
    """
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    id = id["bot_id"]
    if promo.id is not None:
        eid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1", promolid)
        if eid is None:
            return ORJSONResponse({"done":  False, "reason": "NO_PROMOTION_FOUND", "code": 4848}, status_code = 400)
        await db.execute("DELETE FROM bot_promotions WHERE bot_id = $1 AND id = $2", id, promo.id)
    else:
        await db.execute("DELETE FROM bot_promotions WHERE bot_id = $1", id)
    return {"done":  True, "reason": None, "code": 1000}

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

@router.patch("/bots/admin/{bot_id}/under_review", response_model = APIResponse)
async def bot_under_review_api(request: Request, bot_id: int, data: BotUnderReview, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    """
    Put a bot in queue under review or back in queue. This is internal and only meant for our test server manager bot
    """
    if not secure_strcmp(Authorization, test_server_manager_key):
        return abort(401)
    admin_tool = BotListAdmin(bot_id, data.mod)
    if data.requeue:
        state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1 AND state = $2", bot_id, enums.BotState.under_review)
        if state is None:
            return abort(404)
        rc = await admin_tool.unban_requeue_bot(state)
    else:
        rc = await admin_tool.claim_bot()
    if rc is not None:
        return abort(404) # A wrror here means 404
    return {"done": True, "reason": None, "code": 1000}

@router.get("/bots/admin/queue", response_model = BotQueueGet)
async def botlist_get_queue_api(request: Request):
    bots = await db.fetch("SELECT bot_id FROM bots WHERE state = $1", enums.BotState.pending)
    return {"bots": [(await get_bot(bot["bot_id"])) for bot in bots]}

@router.patch("/bots/admin/{bot_id}/queue", response_model = APIResponse)
async def botlist_edit_queue_api(request: Request, bot_id: int, data: BotQueuePatch, Authorization: str = Header("BOT_TEST_MANAGER_KEY")):
    """
    Admin API to approve/verify or deny a bot on Fates List
    """
    if not secure_strcmp(Authorization, test_server_manager_key):
        return abort(401)
    
    try:
        admin_tool = BotListAdmin(bot_id, int(data.mod))
    except:
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. Please contact the developers of this bot!", "code": 3839}, status_code = 400)
 
    if not data.feedback:
        if data.approve:
            data.feedback = approve_feedback
        else:
            data.feedback = deny_feedback

    if len(data.feedback) < 3:
        return ORJSONResponse({"done": False, "reason": "Feedback must either not be provided or must be larger than 3 characters!", "code": 3836}, status_code = 400)
    guild = client.get_guild(main_server)
    user = guild.get_member(int(data.mod))
    if user is None or not is_staff(staff_roles, user.roles, 2)[0]:
        return ORJSONResponse({"done": False, "reason": "Invalid Moderator specified. The moderator in question does not have permission to perform this action!", "code": 3867}, status_code = 400)

    if data.approve:
        rc = await admin_tool.approve_bot(data.feedback)
    else:
        rc = await admin_tool.deny_bot(data.feedback)
    
    if rc is None:
        if not data.approve:
            return {"done": True, "reason": "Bot Denied Successfully!", "code": 1001}
        return {"done": True, "reason": f"Bot Approved Successfully! Invite it to the main server with https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot&guild_id={guild.id}&disable_guild_select=true&permissions=0", "code": 1001}
    return ORJSONResponse({"done": False, "reason": rc, "code": 3869}, status_code = 400)

@router.get("/bots/random", response_model = BotRandom, dependencies=[Depends(RateLimiter(times=7, minutes=1))])
async def random_bots_api(request: Request):
    random_unp = await db.fetchrow("SELECT description, banner, state, votes, servers, bot_id, invite FROM bots WHERE state = 0 OR state = 6 ORDER BY RANDOM() LIMIT 1") # Unprocessed, use the random function to get a random bot
    bot = (await get_bot(random_unp["bot_id"])) | dict(random_unp) # Get bot from cache and add that in
    bot["bot_id"] = str(bot["bot_id"]) # Make sure bot id is a string to prevent corruption issues
    bot["servers"] = human_format(bot["servers"]) # Format the servers field
    bot["description"] = ireplacem(js_rem_tuple, bot["description"]) # Prevent some basic attacks in short description
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
    owners = await db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", bot_id)
    api_ret["owners"] = [{"owner": str(obj["owner"]), "user": (await get_user(obj["owner"])), "main": obj["main"]} for obj in owners]
    if api_ret["features"] is None:
        api_ret["features"] = []
    bot_obj = await get_bot(bot_id)
    if bot_obj is None:
        return abort(404)
    api_ret = api_ret | bot_obj
    api_ret["vanity"] = await db.fetchval("SELECT vanity_url FROM vanity WHERE redirect = $1", bot_id)
    return api_ret

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
    print(filter, exclude)
    if secure_strcmp(Authorization, test_server_manager_key):
        pass
    else:
        id = await bot_auth(bot_id, Authorization)
        if id is None:
            return abort(401)
    return await get_events(bot_id = bot_id, filter = filter, exclude = exclude)

@router.post("/bots/{bot_id}", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
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

@router.patch("/bots/{bot_id}", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
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
async def get_bot_reviews(request: Request, bot_id: int):
    reviews = await parse_reviews(bot_id)
    if reviews[0] == []:
        return abort(404)
    return {"reviews": reviews[0], "average_stars": reviews[1]}

@router.patch("/bots/{bot_id}/reviews/{rid}/votes", response_model = APIResponse)
async def upvote_review_api(request: Request, bot_id: int, rid: uuid.UUID, vote: BotReviewVote, Authorization: str = Header("USER_TOKEN")):
    id = await user_auth(vote.user_id, Authorization)
    vote.user_id = int(vote.user_id)
    if id is None:
        return abort(401)
    bot_rev = await db.fetchrow("SELECT review_upvotes, review_downvotes FROM bot_reviews WHERE id = $1", rid)
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
    await add_event(bot_id, "review_vote", {"user": str(vote.user_id), "review_id": str(rid), "upvotes": len(bot_rev["review_upvotes"]), "downvotes": len(bot_rev["review_downvotes"]), "upvote": vote.upvote})
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

    await db.execute("DELETE FROM bot_reviews WHERE id = $1", rid)
    bt.add_task(base_rev_bt, bot_id, "delete_review", {"user": data.user_id, "reply": False, "review_id": str(rid)})
    return {"done": True, "reason": None, "code": 1000}

@router.get("/bots/{bot_id}/commands", response_model = BotCommands)
async def get_bot_commands_api(request:  Request, bot_id: int):
    cmd = await get_bot_commands(bot_id)
    if cmd == {}:
        return abort(404)
    return cmd

@router.post("/bots/{bot_id}/commands", response_model = BotCommandAddResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def add_bot_command_api(request: Request, bot_id: int, command: BotCommandAdd, Authorization: str = Header("BOT_TOKEN"), force_add: Optional[bool] = False):
    """
        Self explaining command. Note that if force_add is set, the API will not check if your command already exists and will forcefully add it, this may lead to duplicate commands on your bot. If ret_id is not set, you will not get the command id back in the api response
    """
    if command.slash not in [0, 1, 2]:
        return ORJSONResponse({"done":  False, "reason": "UNSUPPORTED_MODE"}, status_code = 400)

    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)

    if force_add is False:
        check = await db.fetchrow("SELECT name FROM bot_commands WHERE name = $1 AND bot_id = $2", command.name, bot_id)
        if check is not None:
            return ORJSONResponse({"done":  False, "reason": "COMMAND_ALREADY_EXISTS"}, status_code = 400)
    id = uuid.uuid4()
    await db.execute("INSERT INTO bot_commands (id, bot_id, slash, name, description, args, examples, premium_only, notes, doc_link) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)", id, bot_id, command.slash, command.name, command.description, command.args, command.examples, command.premium_only, command.notes, command.doc_link)
    return {"done": True, "reason": None, "id": id, "code": 1001}

@router.patch("/bots/{bot_id}/commands", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def edit_bot_command_api(request: Request, bot_id: int, command: BotCommandEdit, Authorization: str = Header("BOT_TOKEN")):
    if command.slash not in [0, 1, 2]:
        return ORJSONResponse({"done":  False, "reason": "UNSUPPORTED_MODE"}, status_code = 400)

    id = await bot_auth(bot_id, Authorization)
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
    return {"done": True, "reason": None, "code": 1000}

@router.delete("/bots/{bot_id}/commands", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def delete_bot_command_api(request: Request, bot_id: int, command: BotCommandDelete, Authorization: str = Header("BOT_TOKEN")):
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    await db.execute("DELETE FROM bot_commands WHERE id = $1 AND bot_id = $2", command.id, bot_id)
    return {"done": True, "reason": None, "code": 1000}

@router.get("/bots/{bot_id}/votes", response_model = BotVoteCheck, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
async def get_votes_api(request: Request, bot_id: int, user_id: Optional[int] = None, Authorization: str = Header("BOT_TOKEN")):
    """Endpoint to check amount of votes a user has."""
    if user_id is None:
        return dict((await db.fetchrow("SELECT votes FROM bots WHERE bot_id = $1", bot_id))) | {"vote_epoch": 0, "voted": False, "time_to_vote": 1, "vote_right_now": False}
    id = await bot_auth(bot_id, Authorization)
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
        ret[str(data["user_id"])] = data["timestamps"]
    return {"timestamped_votes": ret}

@router.post("/bots/{bot_id}/stats", response_model = APIResponse, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
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

@router.get("/vanity/{vanity}", response_model = BotVanity)
async def get_vanity(request: Request, vanity: str):
    vb = await vanity_bot(vanity, compact = True)
    if vb is None:
        return abort(404)
    return {"type": vb[0], "redirect": vb[1]}

@router.get("/index/bots", response_model = BotIndex)
async def bots_index_page(request: Request):
    """For any potential Android/iOS app, crawlers etc."""
    return await render_index(request = request, api = True)

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

@router.get("/users/{user_id}", response_model = User)
async def get_user_api(request: Request, user_id: int):
    user = await db.fetchrow("SELECT state, description, css FROM users WHERE user_id = $1", user_id)
    if user is None or user["state"] == enums.UserState.ddr_ban:
        return abort(404)
    user_obj = await get_user(user_id)
    user_ret = dict(user) | user_obj
    return user_ret

@router.post("/users/{user_id}/servers/prepare", dependencies=[Depends(RateLimiter(times=1, seconds=30))], response_model = ServerListAuthed)
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
            print(guild.id)
            guild_json = {"icon": str(guild.icon_url), "name": guild.name, "member_count": guild.member_count, "created_at": str(guild.created_at.timestamp()), "code": get_token(37)}
            await redis_db.hset(str(guild.id), key = "cache", value = orjson.dumps(guild_json))
            valid = valid | {str(guild.id): guild_json}
    print(valid)
    return {"servers": valid, "access_token": access_token}

@router.patch("/users/{user_id}/description", response_model = APIResponse)
async def set_user_description_api(request: Request, user_id: int, desc: UserDescEdit, Authorization: str = Header("USER_TOKEN")):
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

