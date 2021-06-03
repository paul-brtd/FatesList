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
        return ORJSONResponse({"done":  False, "reason": "Text is too small", "code": 9898}, status_code = 400)
    if promo.type not in [1, 2, 3]:
        return ORJSONResponse({"done":  False, "reason": "Invalid promotion type provided ", "code": 9897}, status_code = 400)
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
        return ORJSONResponse({"done":  False, "reason": "Text is too small", "code": 2919}, status_code = 400)
    if promo.type not in [1, 2, 3]:
        return ORJSONResponse({"done":  False, "reason": "Invalid promotion type provided ", "code": 9897}, status_code = 400)
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        return abort(401)
    pid = await db.fetchrow("SELECT id FROM bot_promotions WHERE id = $1 AND bot_id = $2", promo.id, bot_id)
    if pid is None:
        return ORJSONResponse({"done":  False, "reason": "NO_PROMOTION_FOUND", "code": 2917}, status_code = 400)
    await db.execute("UPDATE bot_promotions SET title = $1, info = $2, type = $3 WHERE bot_id = $4 AND id = $5", promo.title, promo.info, promo.type, bot_id, promo.id)
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
