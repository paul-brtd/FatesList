from math import ceil

from modules.core import *

from ..base import API_VERSION
from .models import APIResponse, BotVoteCheck

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Votes"]
)

@router.get(
    "/users/{user_id}/bots/{bot_id}/votes", 
    response_model = BotVoteCheck, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            )
        ),
        Depends(bot_user_auth_check)
    ]
)
async def get_user_votes(request: Request, bot_id: int, user_id: int):
    """Endpoint to check amount of votes a user has."""
    voter_ts = await db.fetchval(
        "SELECT timestamps FROM bot_voters WHERE bot_id = $1 AND user_id = $2", 
        bot_id, 
        user_id
    )
    
    vote_epoch = await redis_db.ttl(f"vote_lock:{user_id}")

    voter_count = len(voter_ts) if voter_ts else 0
    
    return {
        "votes": voter_count, 
        "voted": voter_count != 0, 
        "vote_epoch": vote_epoch, 
        "vts": voter_ts, 
        "time_to_vote": 60*60*8 - vote_epoch if vote_epoch else 0, 
        "vote_right_now": vote_epoch == -2, 
        "type": "Vote", 
        "reason": None, 
        "partial": False
    }

@router.patch(
    "/users/{user_id}/bots/{bot_id}/votes",
    response_model = APIResponse,
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=5, minutes=1)
            )
        ),
        Depends(user_auth_check)
    ]
)
async def create_vote(user_id: int, bot_id: int):
    """Endpoint to create a vote for a bot"""
    ret = await vote_bot(redis = redis_db, user_id = user_id, bot_id = bot_id, test = False)
    if ret is True: 
        return api_success()
    elif ret is None: 
        return abort(404)
    else:
        total_seconds = ret
        wait_time = {}
        
        # Get wait time
        wait_time["minutes"], wait_time["seconds"] = divmod(total_seconds, 60)
        wait_time["hours"], wait_time["minutes"] = divmod(wait_time["minutes"], 60)
        wait_time["total"] = total_seconds
                
        return api_error(
            "You can't vote for this bot yet!",
            wait_time = wait_time,
            headers = {"Retry-After": str(total_seconds)}
        )              
        
@router.post("/bots/{bot_id}/testhook", dependencies = [Depends(bot_auth_check)])
async def send_test_webhook(bot_id: int):
    """Endpoint to test webhooks"""
    return await vote_bot(
        redis = redis_db,
        user_id = 519850436899897346, 
        bot_id = bot_id, 
        test = True, 
    )
