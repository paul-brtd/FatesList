from modules.core import *
from lynxfall.utils.string import intl_text

from ..base import API_VERSION
from .models import APIResponse, BotReviewPartial

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/users",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Reviews"],
    dependencies=[
        Depends(id_check("bot")),
        Depends(id_check("user")),
        Depends(user_auth_check)
    ]
)

@router.post("/{user_id}/bots/{bot_id}/reviews", response_model=APIResponse)
async def new_review(request: Request, user_id: int, bot_id: int, data: BotReview):
    minlength = 10
    if len(data.review) < minlength:
        return api_error(
            f"Reviews must be at least {minlength} characters long"
        )

    db = request.app.state.worker_session.postgres
    if not data.reply:
        check = await db.fetchval(
            "SELECT id FROM bot_reviews WHERE bot_id = $1 AND user_id = $2 AND reply = false", bot_id, user_id
        )
    
        if check:
            return api_error(
                "You have already made a review for this bot, please edit that one instead of making a new one!",
                id=str(check)
            )
    else:
        check = await db.fetchval("SELECT id FROM bot_reviews WHERE id = $1", data.id)
        if not check:
            return abort(404)
        
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
        await db.execute("UPDATE bot_reviews SET replies = replies || $1 WHERE id = $2", [id], data.id)
        
    await bot_add_event(
        bot_id, 
        enums.APIEvents.review_add,
        {
            "user": str(user_id), 
            "reply": data.reply,
            "id": str(id),
            "star_rating": data.star_rating,
            "review": data.review,
            "root": data.id
        }
    )
    return api_success()


@router.patch("/{user_id}/bots/{bot_id}/reviews/{id}", response_model=APIResponse)
async def edit_review(request: Request, user_id: int, bot_id: int, id: uuid.UUID, data: BotReview):
    """Deletes a review. Note that the id and the reply flag is not honored for this endpoint"""
    
    check = await db.fetchrow(
        "SELECT COUNT(1) FROM bot_reviews WHERE id = $1 AND bot_id = $2 AND user_id = $3", 
        id,
        bot_id, 
        user_id
    )
        
    if not check:       
        return abort(404)
        
    await db.execute(
        "UPDATE bot_reviews SET star_rating = $1, review_text = $2, epoch = epoch || $3 WHERE id = $4", 
        data.star_rating, 
        data.review, 
        [time.time()],
        id
    )

    await bot_add_event(
        bot_id, 
        enums.APIEvents.review_edit,
        {
            "user": str(user_id), 
            "id": str(id),
            "star_rating": data.star_rating,
            "review": data.review
        }
    )
    return api_success()
    
    
@router.delete("/users/{user_id}/bots/{bot_id}/reviews/{id}", response_model = APIResponse)
async def delete_review(request: Request, user_id: int, bot_id: int, id: uuid.UUID):
    check = await db.fetchrow(
        "SELECT reply, replies FROM bot_reviews WHERE id = $1 AND bot_id = $2 AND user_id = $3", 
        id, 
        bot_id, 
        user_id
    )
    
    if check is None:
        return abort(404)
    
    await db.execute("DELETE FROM bot_reviews WHERE id = $1", id)
    for review in event_data["replies"]:
        await db.execute("DELETE FROM bot_reviews WHERE id = $1", review)
        
    await bot_add_event(
        bot_id, 
        enums.APIEvents.review_delete,
        {
            "user": str(user_id),
            "reply": check["reply"],
            "id": str(id)
        }
    )
    return api_success()    
