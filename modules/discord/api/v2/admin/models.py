from pydantic import BaseModel, validator
import modules.models.enums as enums
from ..base_models import BaseUser, APIResponse, IDResponse
from typing import Optional, List
import uuid

class BotListAdminRoute(BaseModel):
    mod: str

    @validator('mod')
    def mod_int(cls, v, values, **kwargs):
        if not v.isdigit():
            raise ValueError('Mod must be a integer')
        return int(v)

class BotListPartner(BotListAdminRoute):
    type: enums.PartnerType
    partner: str
    edit_channel: str # Edit channel for partnership (where the ad will be sent and/or updated
    invite: str # Support server or partnered server invite
    id: Optional[str] = None
 
    @validator('id')
    def id_if_bot(cls, v, values, **kwargs):
        if values.get("type") != enums.PartnerType.bot:
            return int(v) if v.isdigit() else None
        elif v is None or not v.isdigit():
            raise ValueError('Bots must have a ID set')
        return v
    
    @validator('edit_channel')
    async def edit_channel_int(cls, v, values, **kwargs):
        if not v.isdigit():
            raise ValueError('Edit channel must be a integer')
        return int(v)
    
class BotListPartnerAd(BotListAdminRoute):
    pid: uuid.UUID
    ad: str
        
class BotListPartnerChannel(BotListAdminRoute):
    pid: uuid.UUID
    publish_channel: str  
        
    @validator('publish_channel')
    async def edit_channel_int(cls, v, values, **kwargs):
        if not v.isdigit():
            raise ValueError('Publish channel must be a integer')
        return int(v)
        
class BotLock(BotListAdminRoute):
    reason: str
    lock: bool

class BotStateUpdate(BaseModel):
    state: enums.BotState

class BotTransfer(BotListAdminRoute):
    new_owner: str

class BotQueueAdminPatch(BotListAdminRoute):
    op: enums.AdminQueueOp
    reason: Optional[str] = None

class PartialBotQueue(BaseModel):
    user: BaseUser
    prefix: str
    invite: str
    description: str

class BotQueueList(BaseModel):
    __root__: List[PartialBotQueue]

class BotQueueGet(BaseModel):
    bots: BotQueueList

