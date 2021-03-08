from ..deps import *

router = APIRouter(
    prefix = "/server",
    tags = ["Server Actions"],
    include_in_schema = False
)

@router.get("/admin/add")
async def add_server_main(request: Request):
    if "userid" in request.session.keys():
        if request.session.get("server_list"):
            return templates.TemplateResponse("server_add_s1.html", {"request": request, "tags_fixed": server_tags_fixed, "data": {"access_token": request.session.get("access_token"), "scopes": request.session.get("dscopes_str")}, "error": None, "step": 1, "invite": server_bot_invite})
        else:
            return templates.e(request, "You must login with Server Listing enabled<br/>Please logout and login again.", status_code = 400)
    else:
        return RedirectResponse("/auth/login?redirect=/server/admin/add&pretty=to add a server")

