from modules.core import *
from lynxfall.utils.string import human_format, intl_text
from fastapi.responses import PlainTextResponse

from ..base import API_VERSION
from .models import APIResponse, Bot, BotRandom, BotStats, BotAppeal

cleaner = Cleaner(remove_unknown_tags=False)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/bots",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Bots"],
    dependencies=[Depends(id_check("bot"))]
)


if "user_id" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to review this bot", status_code = 303)
    check = await db.fetchrow("SELECT bot_id FROM bot_reviews WHERE bot_id = $1 AND user_id = $2 AND reply = false", bot_id, int(request.session["user_id"]))
    if check is not None:
        return await templates.TemplateResponse("message.html", {"request": request, "message": "You have already made a review for this bot, please edit that one instead of making a new one!"})
    id = uuid.uuid4()
    await db.execute("INSERT INTO bot_reviews (id, bot_id, user_id, star_rating, review_text, epoch) VALUES ($1, $2, $3, $4, $5, $6)", id, bot_id, int(request.session["user_id"]), rating, review, [time.time()])
    await bot_add_event(bot_id, enums.APIEvents.review_add, {"user": str(request.session["user_id"]), "reply": False, "id": str(id), "star_rating": rating, "review": review, "root": None})
    return await templates.TemplateResponse("message.html", {"request": request, "message": f"Successfully made a review for this bot!<script>window.location.replace('/bot/{bot_id}')</script>"}) 
