from modules.core import *
from lynxfall.utils.string import intl_text

from ..base import API_VERSION
from .models import APIResponse

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/users",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Reviews"],
    dependencies=[
        Depends(id_check("bot")),
        Depends(id_check("user"))
    ]
)

@router.post("/{user_id}/bots/{bot_id}/reviews", response_model=APIResponse)
async def new_review(request: Request, user_id: int, bot_id: int, data: BotReviewPartial):
    db = request.app.state.worker_session.postgres
    if not data.reply:
        check = await db.fetchval(
            "SELECT id FROM bot_reviews WHERE bot_id = $1 AND user_id = $2 AND reply = false", bot_id, user_id
        )
    
        if check:
            return api_error(
                "You have already made a review for this bot, please edit that one instead of making a new one!",
                id=check
            )
    else:
        replies = await db.fetchval("SELECT replies FROM bot_reviews WHERE id = $1", data.id)
        if not replies:
            return api_error(
                "You are not allowed to reply to this review as it doesn't actually exist"
            )
        
    id = uuid.uuid4()
    await db.execute(
        "INSERT INTO bot_reviews (id, bot_id, user_id, star_rating, review_text, epoch, reply) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        id,
        bot_id, 
        user_id,
        data.star_rating, 
        data.review, 
        [time.time()],
        data.reply
    )
    
    if data.reply:
        replies.append(id)
        await db.execute("UPDATE bot_reviews SET replies = replies || $1 WHERE id = $2", id, data.id)

    
    await bot_add_event(bot_id, enums.APIEvents.review_add, {"user": str(user_id), "reply": False, "id": str(id), "star_rating": rating, "review": review, "root": None})
    return api_success()
