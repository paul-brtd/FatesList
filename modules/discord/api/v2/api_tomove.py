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
