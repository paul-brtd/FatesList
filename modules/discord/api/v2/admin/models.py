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
