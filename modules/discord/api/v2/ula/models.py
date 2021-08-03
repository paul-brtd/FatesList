from pydantic import BaseModel

from typing import List, Dict, Optional

import modules.models.enums as enums

from ..base_models import APIResponse

class Lists(BaseModel):
    lists: dict

class Stats(Lists):
    server_count: int
    shard_count: Optional[int] = None
    user_count: Optional[int] = None
    shards: Optional[List[int]] = None
    shard_id: Optional[int] = None

class BList(BaseModel):
    url: str
    icon: Optional[str] = None
    api_url: str
    api_docs: str
    discord: Optional[str] = None
    description: Optional[str] = "No Description Yet :("
    supported_features: List[int]
    owners: List[str]

class Endpoint(BaseModel):
    method: enums.ULAMethod
    feature: enums.ULAFeature
    api_path: str
    supported_fields: dict

class Supported:
    post_stats = ("server_count", "shard_count", "shards", "shard_id", 'bot_id', "user_count")
    get_user_voted = ('user_id', 'voted') # Get User Votes
