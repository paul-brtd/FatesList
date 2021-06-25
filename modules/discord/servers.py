import io

import markdown
from starlette.responses import StreamingResponse

from ..core import *

router = APIRouter(
    prefix = "/server",
    tags = ["Servers"],
    include_in_schema = False
)

@router.get("/{guild_id}")
async def server_index(request: Request, guild_id: int, bt: BackgroundTasks, rev_page: int = 1):
    return await render_server(request, guild_id = guild_id, bt = bt, api = False, rev_page = rev_page)

#@router.get("/{bot_id}/widget")
#async def bot_widget(request: Request, bot_id: int, bt: BackgroundTasks):
#    return await render_bot_widget(request, bt, bot_id, api = False)

#@router.get("/{bot_id}/invite")
#async def bot_invite_and_log(request: Request, bot_id: int):
#    if "user_id" not in request.session.keys():
#        user_id = 0
#    else:
#        user_id = int(request.session.get("user_id"))
#    invite = await invite_bot(bot_id, user_id = user_id)
#    if invite is None:
#        return abort(404)
#    return RedirectResponse(invite)

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
