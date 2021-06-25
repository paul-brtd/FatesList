from typing import Optional

from modules.core import *

from ..base import API_VERSION
from .models import BotListStats

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/blstats",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Stats"]
)

@router.get(
    "/", 
    response_model = BotListStats
)
async def botlist_stats_api(
    request: Request,
):
    """
        Returns uptime and stats about the list.
        uptime - The current uptime for the given worker
        pid - The pid of the worker you are connected to
        up - Whether the databases are up on this worker
        dup - Whether we have connected to discord on this worker
        bot_count_total - The bot count of the list
        bot_count - The approved and certified bots on the list

        An additional workers list will be populated from RabbitMQ if possible
    """
    if up:
        bot_count_total = await db.fetchval("SELECT COUNT(1) FROM bots")
        bot_count = await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    else:
        bot_count = 0
        bot_count_total = 0
    worker_ret = await add_rmq_task_with_ret("_worker", {})
    if worker_ret[1]:
        worker_lst = worker_ret[0]["ret"]
    else:
        worker_lst = []
    return {
        "uptime": time.time() - boot_time, 
        "pid": os.getpid(), 
        "up": up, 
        "dup": (client.user is not None), 
        "bot_count": bot_count, 
        "bot_count_total": bot_count_total,
        "workers": worker_lst
    }
