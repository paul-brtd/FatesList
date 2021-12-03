import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser, IDResponse


class BotCommand(BaseModel):
    cmd_type: enums.CommandType  # 0 = no, 1 = guild, 2 = global
    cmd_groups: list[str] | None = ["Default"]
    cmd_name: str
    vote_locked: bool
    description: str
    args: list | None = ["<user>"]
    examples: list | None = []
    premium_only: bool | None = False
    notes: list | None = []
    doc_link: str | None = ""


class BotCommandWithId(BotCommand):
    id: uuid.UUID


class BotCommandsGet(BaseModel):
    __root__: dict[str, list[BotCommandWithId]]


class BotCommands(BaseModel):
    commands: list[BotCommand]


class BotCommandDelete(BaseModel):
    ids: list[uuid.UUID] | None = None
    names: list[str] | None = None
    nuke: bool | None = False

    @validator("nuke")
    def nuke_check(cls, v, values, **kwargs):
        if "ids" in values:
            if values["ids"] and v:
                raise ValueError(
                    "ids and nuke cannot be used at the same time!")
        if "name" in values:
            if values["names"] and v:
                raise ValueError(
                    "names and nuke cannot be used at the same time!")
        return v
