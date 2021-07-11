from modules.core import *
from ..base import API_VERSION
from config import privacy_policy as pp
from config import bot_requirements as br

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/policies",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Policies"]
)

@router.get("/privacy")
async def privacy_policy(request: Request):
    return pp
