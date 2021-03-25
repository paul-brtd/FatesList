from ..deps import *

router = APIRouter(
    prefix = "/pack",
    tags = ["Pack Actions"],
    include_in_schema = False
)

@router.get("/admin/add")
async def add_server_main(request: Request):
    if "userid" in request.session.keys():
        return await templates.TemplateResponse("pack_add_edit.html", {"request": request, "tags_fixed": server_tags_fixed, "data": {"form": (await Form.from_formdata(request))}, "error": None, "mode": "add"})
    else:
        return RedirectResponse("/auth/login?redirect=/pack/admin/add&pretty=to add a bot pack")

