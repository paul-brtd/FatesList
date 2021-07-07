from ..core import *

router = APIRouter(
    prefix = "/server",
    tags = ["Server Actions"],
    include_in_schema = False
)

@router.get("/admin/add")
async def add_server_main(request: Request, worker_session = Depends(worker_session)):
    oauth = worker_session.oauth
    if "user_id" in request.session.keys():
        scopes = orjson.loads(request.session["scopes"])
        access_token = orjson.loads(request.session["access_token"])
        access_token = await oauth.discord.refresh_access_token(AccessToken(**access_token))
        request.session["access_token"] = orjson.dumps(access_token.dict()).decode("utf-8")

        if "guilds" in scopes:
            return await templates.TemplateResponse("server_add.html", {"request": request, "invite": server_bot_invite, "scopes": scopes, "access_token": access_token.access_token})
        else:
            return await templates.e(request, "You must login with Server Listing enabled", main = "Please logout and login again.", status_code = 400)
    else:
        return RedirectResponse("/auth/login?redirect=/server/admin/add&pretty=to add a server")

