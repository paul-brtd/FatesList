from modules.core import *
from .models import BotPromotionPartial, BotPromotion, BotPromotions, BotPromotionPartial, BotPromotionDelete, APIResponse
from ..base import API_VERSION

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Promotions"]
)

@router.get(
    "/bots/{bot_id}/promotions", 
    response_model = BotPromotions
)
async def get_promotion(request:  Request, bot_id: int):
    promos = await get_promotions(bot_id)
    if promos == []:
        return abort(404)
    return {"promotions": promos}

@router.post(
    "/bots/{bot_id}/promotions",
    response_model = APIResponse, 
    dependencies = [
        Depends(bot_auth_check)
    ]
)
async def add_promotion(request: Request, bot_id: int, promo: BotPromotionPartial):
    """Creates a promotion for a bot. Type can be 1 for announcement, 2 for promotion or 3 for generic"""
    await add_promotion(bot_id, promo.title, promo.info, promo.css, promo.type)
    return api_success()

@router.patch(
    "/bots/{bot_id}/promotions", 
    response_model = APIResponse,
    dependencies = [
        Depends(bot_auth_check)
    ]
)
async def edit_promotion(request: Request, bot_id: int, promo: BotPromotion):
    """Edits an promotion for a bot given its promotion ID.
    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb
    **Promotion ID**: This is the ID of the promotion you wish to edit 
    """
    pid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1 AND bot_id = $2", promo.id, bot_id)
    if pid is None:
        return api_error(
            "Promotion not found",
            status_code = 404
        )
    await db.execute(
        "UPDATE bot_promotions SET title = $1, info = $2, type = $3 WHERE bot_id = $4 AND id = $5", 
        promo.title, 
        promo.info, 
        promo.type,
        bot_id, 
        promo.id
    )
    return api_success()

@router.delete(
    "/bots/{bot_id}/promotions", 
    response_model = APIResponse,
    dependencies = [
        Depends(bot_auth_check)
    ]
)
async def delete_promotion(request: Request, bot_id: int, promo: BotPromotionDelete):
    """Deletes a promotion for a bot or deletes all promotions from a bot
    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb
    **Event ID**: This is the ID of the event you wish to delete. Not passing this will delete ALL events, so be careful
    """
    if promo.id is not None:
        eid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1", promo.id)
        if eid is None:
            return api_error(
                "Promotion not found",
                status_code = 404
            )
        await db.execute("DELETE FROM bot_promotions WHERE bot_id = $1 AND id = $2", bot_id, promo.id)
    else:
        await db.execute("DELETE FROM bot_promotions WHERE bot_id = $1", bot_id)
    return api_success()
