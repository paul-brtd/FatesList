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
    bot = await db.fetchrow("SELECT long_description FROM bots WHERE bot_id = $1",int(bot_id))
    if bot:
        return templates.TemplateResponse("description.html",{"request":request,"long_description": markdown.markdown(bot['long_description'])})
    else:
        return "Bot not found! :( Try refreshing. After that either report it on the support server or just continue your day!"

@router.get("/{bot_id}/widget")
async def bot_widget(request: Request, bot_id: int):
    return await render_bot(request, bot_id, review = False, widget = True)
