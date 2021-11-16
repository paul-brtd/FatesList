import io

import markdown
from starlette.responses import StreamingResponse
from fastapi import Response
from modules.core import constants

from ..core import *

router = APIRouter(
    prefix = "/server",
    tags = ["Servers"],
    include_in_schema = False
)

@router.get("/")
async def guild_rdir(request: Request):
    return "WIP"

@router.get("/{guild_id}")
async def guild_page(request: Request, guild_id: int, bt: BackgroundTasks, rev_page: int = 1):
    data = await db.fetchrow("SELECT guild_id, invite_amount, avatar_cached, name_cached, votes, css, description, long_description, long_description_type FROM servers WHERE guild_id = $1", guild_id)
    if not data:
        return abort(404)
    data = dict(data)
    data["user"] = {
        "username": data["name_cached"],
        "avatar": data["avatar_cached"]
    }
    context = {"type": "server", "replace_list": constants.long_desc_replace_tuple, "id": str(guild_id)}
    data["type"] = "server"
    data["id"] = str(guild_id)
    return await templates.TemplateResponse("bot_server.html", {"request": request, "replace_last": replace_last, "data": data} | data, context = context)

@router.get("/{guild_id}/reviews_html")
async def guild_review_page(request: Request, guild_id: int, page: int = 1):
    return ""
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


#@router.get("/{guild_id}/invite")
async def bot_invite_and_log(request: Request, bot_id: int):
    if "user_id" not in request.session.keys():
        user_id = 0
    else:
        user_id = int(request.session.get("user_id"))
    invite = await invite_bot(bot_id, user_id = user_id)
    if invite is None:
        return abort(404)
    return RedirectResponse(invite)

#@router.get("/{bot_id}/banner")
async def banner(request: Request, bot_id: int):
    bot = await db.fetchrow("SELECT banner FROM bots WHERE bot_id = $1", bot_id)
    if bot is None:
        return abort(404)
    if bot["banner"] in ["none", ""]:
        banner = "https://fateslist.xyz/static/assets/img/banner.webp"
    else:
        banner = bot["banner"]
    banner = await requests.get(banner)
    img = banner
    if img.headers.get("Content-Type") is None or img.headers.get("Content-Type").split("/")[0] != "image":
        return abort(400)
    banner = await banner.read()
    return StreamingResponse(io.BytesIO(banner), media_type = img.headers.get("Content-Type"))

@router.get("/{guild_id}/vote")
async def vote_bot_get(request: Request, bot_id: int):
    bot = await db.fetchrow("SELECT bot_id, votes, state FROM bots WHERE bot_id = $1", bot_id)
    if bot is None:
        return abort(404)
    bot_obj = await get_bot(bot_id)
    if bot_obj is None:
        return abort(404)
    bot = dict(bot) | bot_obj
    return await templates.TemplateResponse("vote.html", {"request": request, "bot": bot})
