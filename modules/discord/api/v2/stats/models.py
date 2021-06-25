from typing import List, Optional

from pydantic import BaseModel


class BotListStats(BaseModel):
    uptime: float
    pid: int
    up: bool
    dup: bool
    bot_count: int
    bot_count_total: int
    workers: Optional[List[int]] = []
