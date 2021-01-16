from ..deps import *
from uuid import UUID

router = APIRouter(
    prefix = "/apiweb",
    tags = ["API Web GUI"]
)

@router.get("/{api_token}")
async def apiweb_main(request: Request, api_token: str):
    if request.session.get("username") is None:
        return RedirectResponse("/")
    fetch = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", api_token)
    if fetch is None:
        return abort(404)
    return templates.TemplateResponse("apiweb.html", {"request": request, "username": request.session.get("username", False), "avatar": request.session.get("avatar"), "api_token": api_token, "bot_id": fetch["bot_id"]})  
