from modules.core import *
from ..base import API_VERSION
from config import privacy_policy as pp

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/privacy",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Privacy"]
)

@router.get("/policy")
async def privacy_policy(request: Request):
    return pp
