from modules.core import *
from .models import APIResponse, BotVoteCheck
from ..base import API_VERSION

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Votes"]
)

@router.get("/bots/{bot_id}/votes", response_model = BotVoteCheck, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
async def get_votes(request: Request, bot_id: int, user_id: Optional[int] = None, Authorization: str = Header("BOT_TOKEN")):
    """Endpoint to check amount of votes a user or the whole bot has."""
    if user_id is None:
        votes = await db.fetchval("SELECT votes FROM bots WHERE bot_id = $1", bot_id)
        return {"votes": votes, "voted": votes != 0, "type": "BotVote", "reason": "No User ID set", "partial": True}
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    voter_count = await db.fetchval("SELECT cardinality(timestamps) FROM bot_voters WHERE bot_id = $1 AND user_id = $2", int(bot_id), int(user_id))
    voter_count = voter_count if voter_count else 0
    ret = await vote_bot(user_id = user_id, bot_id = bot_id, autovote = False, test = False, pretend = True)
    if ret is None:
        return {"votes": voter_count, "voted": voter_count != 0, "type": "VNFVote", "reason": "Voter not found!", "partial": True}
    return {"votes": voter_count, "voted": voter_count != 0, "vote_epoch": ret[0].timestamp() if isinstance(ret, tuple) else 0, "time_to_vote": ret[1].total_seconds() if isinstance(ret, tuple) else 0, "vote_right_now": ret == True, "type": "Vote", "reason": None, "partial": False}
