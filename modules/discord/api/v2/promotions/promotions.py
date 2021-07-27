from modules.core import *

from ..base import API_VERSION
from .models import (APIResponse, BotPromotion, BotPromotions)

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
    """Returns all the promotions for a bot on Fates List"""
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
async def add_promotion(request: Request, bot_id: int, promo: BotPromotion):
    """Creates a promotion for a bot. Type can be 1 for announcement, 2 for promotion or 3 for generic"""
    await add_promotion(bot_id, promo.title, promo.info, promo.css, promo.type)
    return api_success()

@router.patch(
    "/bots/{bot_id}/promotions/{id}", 
    response_model = APIResponse,
    dependencies = [
        Depends(bot_auth_check)
    ]
)
async def edit_promotion(request: Request, bot_id: int, promo: BotPromotion, id: uuid.UUID):
    """Edits an promotion for a bot given its promotion ID."""
    pid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1 AND bot_id = $2", id, bot_id)
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
        id
    )
    return api_success()

@router.delete(
    "/bots/{bot_id}/promotions/{id}", 
    response_model = APIResponse,
    dependencies = [
        Depends(bot_auth_check)
    ]
)
async def delete_promotion(request: Request, bot_id: int, id: uuid.UUID):
    """Deletes a bots promotion"""
    eid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1", id)
    if eid is None:
        return api_error(
            "Promotion not found",
            status_code = 404
        )
    await db.execute("DELETE FROM bot_promotions WHERE bot_id = $1 AND id = $2", bot_id, id)
    return api_success()
