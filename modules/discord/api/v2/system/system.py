from typing import Optional

from modules.core import *

from ..base import API_VERSION
from .models import BotListStats

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - System"]
)

@router.get(
    "/blstats", 
    response_model = BotListStats,
    operation_id="blstats"
)
async def get_botlist_stats(
    request: Request,
    worker_session = Depends(worker_session)
):
    """
        Returns uptime and stats about the list.
        uptime - The current uptime for the given worker
        pid - The pid of the worker you are connected to
        up - Whether the databases are up on this worker
        dup - Always true now, but used to be: Whether we have connected to discord on this worker
        bot_count_total - The bot count of the list
        bot_count - The approved and certified bots on the list
        workers - The worker pids
    """
    up = worker_session.up
    db = worker_session.postgres
    if up:
        bot_count_total = await db.fetchval("SELECT COUNT(1) FROM bots")
        bot_count = await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    else:
        bot_count = 0
        bot_count_total = 0
    return {
        "uptime": time.time() - worker_session.start_time, 
        "pid": os.getpid(), 
        "up": up, 
        "dup": True,
        "bot_count": bot_count, 
        "bot_count_total": bot_count_total,
        "workers": worker_session.workers
    }

@router.get("/features")
def get_features(request: Request):
    """Returns all of the features the list supports and information about them. Keys indicate the feature id and value is feature information. The value should but may not always have a name, type and a description keys in the json"""
    return features

@router.get("/tags")
def get_tags(request: Request):
    """These are the tags the list supports. The key is the tag name and the value is the iconify class we use"""
    return TAGS
