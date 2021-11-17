"""Modules to move"""
from typing import Dict, List
from uuid import UUID

from fastapi.responses import HTMLResponse

from modules.core import *
import markdown
from modules.discord.api.v2.modelstomove import *  # TODO

API_VERSION = 2 # This is the API version

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - To Move"]
)

@router.get(
    "/code/{vanity}", 
    response_model = BotVanity
)
async def get_vanity(request: Request, vanity: str):
    vb = await vanity_bot(vanity)
    logger.trace(f"Vanity is {vanity} and vb is {vb}")
    if vb is None:
        return abort(404)
    return {"type": vb[1], "redirect": str(vb[0])}

@router.get(
    "/index",
    response_model=BotIndex
)
async def get_index(request: Request, cert: Optional[bool] = True, type: enums.ReviewType = enums.ReviewType.bot):
    """For any potential Android/iOS app, crawlers etc."""
    return await render_index(request = request, api = True, cert = cert, type=type)

@router.get(
    "/search", 
    response_model = BotSearch,
    dependencies = [
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        )
    ]
)
async def search_list(request: Request, q: str, target_type: enums.SearchType):
    """For any potential Android/iOS app, crawlers etc. Q is the query to search for. Target type is the type to search for"""
    return await render_search(request = request, q = q, api = True, target_type=target_type)
