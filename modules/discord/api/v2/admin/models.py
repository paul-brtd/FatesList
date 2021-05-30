from pydantic import BaseModel
import modules.models.enums as enums

class BotListAdminRoute(BaseModel):
     mod: str

class BotCertify(BotListAdminRoute):
    certify: bool

class BotStateUpdate(BaseModel):
    state: enums.BotState

class BotTransfer(BotListAdminRoute):
    new_owner: str

class BotUnderReview(BotListAdminRoute):
    requeue: enums.BotRequeue

class BotQueuePatch(BotListAdminRoute):
   feedback: Optional[str] = None 
   approve: bool

class PartialBotQueue(BaseModel):
   user: BaseUser
   prefix: str
   invite: str
   description: str

class BotQueueList(BaseModel):
   __root__: List[PartialBotQueue]

class BotQueueGet(BaseModel):
   bots: BotQueueList
