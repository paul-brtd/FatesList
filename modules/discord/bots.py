import io

import markdown
from starlette.responses import StreamingResponse
from fastapi import Response

from ..core import *

router = APIRouter(
    prefix = "/bot",
    tags = ["Bots"],
    include_in_schema = False
)

@router.get("/")
async def bot_rdir(request: Request):
    return RedirectResponse("/")

@router.get("/{bot_id}")
async def bot_index(request: Request, bot_id: int, bt: BackgroundTasks, rev_page: int = 1):
    return await render_bot(
        request, 
        bot_id = bot_id, 
        bt = bt, 
        api = False, 
        rev_page = rev_page, 
    )

@router.get("/{bot_id}/reviews_html", dependencies=[Depends(id_check("bot"))])
async def bot_review_page(request: Request, bot_id: int, page: int = 1):
    page = page if page else 1
    reviews = await parse_reviews(request.app.state.worker_session, bot_id, page=page)
    context = {
        "id": str(bot_id),
        "type": "bot",
        "reviews": {
            "average_rating": float(reviews[1])
        },
    }
    data = {
        "bot_reviews": reviews[0], 
        "average_rating": reviews[1], 
        "total_reviews": reviews[2], 
        "review_page": page, 
        "total_review_pages": reviews[3], 
        "per_page": reviews[4],
    }

    bot_info = await get_bot(bot_id, worker_session = request.app.state.worker_session)
    if bot_info:
        user = dict(bot_info)
        user["name"] = user["username"]
    
    else:
        return await templates.e(request, "Bot Not Found")

    return await templates.TemplateResponse("ext/reviews.html", {"request": request, "data": {"user": user}} | data, context = context)


@router.get("/{bot_id}/invite")
async def bot_invite_and_log(request: Request, bot_id: int):
    if "user_id" not in request.session.keys():
        user_id = 0
    else:
        user_id = int(request.session.get("user_id"))
    invite = await invite_bot(bot_id, user_id = user_id)
    if invite is None:
        return abort(404)
    return RedirectResponse(invite)

@router.get("/{bot_id}/vote")
async def vote_bot_get(request: Request, bot_id: int):
    bot = await db.fetchrow("SELECT bot_id, votes, state FROM bots WHERE bot_id = $1", bot_id)
    if bot is None:
        return abort(404)
    bot_obj = await get_bot(bot_id)
    if bot_obj is None:
        return abort(404)
    bot = dict(bot) | bot_obj
    return await templates.TemplateResponse("vote.html", {"request": request, "bot": bot})
