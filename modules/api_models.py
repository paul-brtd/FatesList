from typing import List, Dict
from pydantic import BaseModel
import uuid

class PromoDelete(BaseModel):
    promo_id: Optional[uuid.UUID] = None

class Promo(BaseModel):
    title: str
    info: str
    css: Optional[str] = None
    type: int

class PromoObj(BaseModel):
    promotions: list

class PromoPatch(Promo):
    promo_id: uuid.UUID

class APIResponse(BaseModel):
    done: bool
    reason: Optional[str] = None

class PartialBotMaint(BaseModel):
    mode: int = 1
    reason: str

class BotMaint(PartialBotMaint):
    epoch: str

class PrevResponse(BaseModel):
    html: str

class PrevRequest(BaseModel):
    html_long_description: bool
    data: str

