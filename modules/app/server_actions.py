from ..deps import *

router = APIRouter(
    prefix = "/server",
    tags = ["Server Actions"],
    include_in_schema = False
)

@router.get("/admin/add")
async def add_server_main(request: Request):
    return RedirectResponse("/server/admin/add/1")

@router.get("/admin/add/1")
async def add_server_step1(request: Request):
    if "userid" in request.session.keys():
        form = await Form.from_formdata(request)
        return templates.TemplateResponse("server_add_s1.html", {"request": request, "tags_fixed": server_tags_fixed, "data": {"form": form}, "error": None, "step": 1, "invite": server_bot_invite})
    else:
        return RedirectResponse("/auth/login?redirect=/server/admin/add&pretty=to add a server")

