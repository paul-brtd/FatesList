"""Modules to move"""
from typing import Dict, List
from uuid import UUID

from fastapi.responses import HTMLResponse

from modules.core import *
import markdown
from modules.discord.api.v2.modelstomove import *  # TODO

API_VERSION = 2 # This is the API version

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - To Move"]
)

@router.patch(
    "/bots/{bot_id}/reviews/{rid}/votes", 
    response_model = APIResponse,
    dependencies = [
        Depends(user_auth_check)
    ],
    deprecated=True
)
async def vote_review_api(request: Request, bot_id: int, rid: uuid.UUID, vote: BotReviewVote):
    """This endpoint is being rewritten and should not be relied on outside official clients"""
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
    "/code/{vanity}", 
    response_model = BotVanity
)
async def get_vanity(request: Request, vanity: str):
    vb = await vanity_bot(vanity)
    logger.trace(f"Vanity is {vanity} and vb is {vb}")
    if vb is None:
        return abort(404)
    return {"type": vb[1], "redirect": str(vb[0])}

@router.get(
    "/index",
    response_model=BotIndex
)
async def get_index(request: Request, t: Optional[str] = "bots", cert: Optional[bool] = True):
    """For any potential Android/iOS app, crawlers etc."""
    if t == "bots":
        return await render_index(request = request, api = True, cert = cert)
    return abort(404)

@router.get(
    "/search", 
    response_model = BotSearch,
    dependencies = [
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        )
    ]
)
async def search_list(request: Request, q: str, t: Optional[str] = "bots"):
    """For any potential Android/iOS app, crawlers etc. Q is the query to search for. T is either bots or profiles"""
    if t == "bots":
        return await render_search(request = request, q = q, api = True)
    elif t == "profiles":
        return await render_profile_search(request = request, q = q, api = True)
    return abort(404)
