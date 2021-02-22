from ..deps import *

router = APIRouter(
    prefix = "/server",
    tags = ["Server Actions"],
    include_in_schema = False
)

@router.get("/admin/add")
@csrf_protect
async def add_server(request: Request):
    return templates.TemplateResponse("message.html", {"request": request, "message": "Coming Soon...", "context": "Server Adding is coming soon. Please give us some time to make it better than ever."})
