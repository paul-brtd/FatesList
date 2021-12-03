from typing import Dict, List, Optional

from pydantic import BaseModel

import modules.models.enums as enums

from ..base_models import APIResponse


class Lists(BaseModel):
    lists: dict


class Stats(Lists):
    server_count: int
    shard_count: int | None = None
    user_count: int | None = None
    shards: list[int] | None = None
    shard_id: int | None = None


class BList(BaseModel):
    url: str
    icon: str | None = None
    api_url: str
    api_docs: str
    discord: str | None = None
    description: str | None = "No Description Yet :("
    supported_features: list[int]
    owners: list[str]


class Endpoint(BaseModel):
    method: enums.ULAMethod
    feature: enums.ULAFeature
    api_path: str
    supported_fields: dict


class Supported:
    post_stats = (
        "server_count",
        "shard_count",
        "shards",
        "shard_id",
        "bot_id",
        "user_count",
    )
    get_user_voted = ("user_id", "voted")  # Get User Votes
