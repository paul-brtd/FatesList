import uuid
from typing import List, Optional, Dict

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser, IDResponse

class BotCommand(BaseModel):
    cmd_type: enums.CommandType # 0 = no, 1 = guild, 2 = global
    cmd_groups: Optional[List[str]] = ["Default"]
    cmd_name: str
    vote_locked: bool
    description: str
    args: Optional[list] = ["<user>"]
    examples: Optional[list] = []
    premium_only: Optional[bool] = False
    notes: Optional[list] = []
    doc_link: Optional[str] = ""

class BotCommandWithId(BotCommand):
    id: uuid.UUID

class BotCommandsGet(BaseModel):
    __root__: Dict[str, List[BotCommandWithId]]
