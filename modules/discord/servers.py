from ..deps import *
import markdown
router = APIRouter(
    prefix = "/server",
    tags = ["Servers"],
    include_in_schema = False
)

@router.get("/")
async def server_rdir(request: Request):
    return RedirectResponse("/")

