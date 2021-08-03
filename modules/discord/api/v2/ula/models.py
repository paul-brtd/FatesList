class Lists(BaseModel):
    lists: dict

class Stats(Lists):
    server_count: int
    shard_count: int

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
