from ..core import *

router = APIRouter(
    tags = ["Support"],
    prefix = "/fates/support",
    include_in_schema = False
)

@router.get("/invite")
async def support(request: Request):
    return RedirectResponse(support_url)

