from ..deps import *
import markdown
router = APIRouter(
    prefix = "/bot",
    tags = ["Bots"],
    include_in_schema = False
)

@router.get("/")
async def bot_rdir(request: Request):
    return RedirectResponse("/")

@router.get("/{bot_id}")
async def bot_index(request: Request, bot_id: int):
    return await render_bot(request, bot_id, review = False, widget = False)

@router.get("/{bot_id}/description")
async def bot_desc(request: Request, bot_id: int):
    bot = await db.fetchrow("SELECT html_long_description AS html_ld, long_description FROM bots WHERE bot_id = $1",int(bot_id))
    if bot:
        if not bot["html_ld"]:
            desc = markdown.markdown(bot['long_description'])
        else:
            desc = bot['long_description']
        return templates.TemplateResponse("description.html",{"request":request,"long_description": desc})
    else:
        return "Bot not found! :( Try refreshing. After that either report it on the support server or just continue your day!"

@router.get("/{bot_id}/widget")
async def bot_widget(request: Request, bot_id: int):
    return await render_bot(request, bot_id, review = False, widget = True)

@router.get("/{bot_id}/invite")
async def bot_invite_and_log(request: Request, bot_id: int, bt: BackgroundTasks):
    bot = await db.fetchrow("SELECT invite, invite_amount FROM bots WHERE bot_id = $1", bot_id)
    if bot is None:
        return abort(404)
    bt.add_task(invite_updater_bt, bot_id, bot["invite_amount"] + 1)
    return RedirectResponse(bot["invite"])

async def invite_updater_bt(bot_id, invite_amount):
    return await db.execute("UPDATE bots SET invite_amount = $1 WHERE bot_id = $2", invite_amount, bot_id)
