from ..core import *
router = APIRouter(
    tags = ["Servers Index"],
    include_in_schema = False
)

@router.get("/server")
@router.get("/servers")
@router.head("/server")
@router.head("/servers")
async def server_rdir(request: Request):
    pass
