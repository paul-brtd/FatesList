from modules.core import *
from .models import BotCertify
from modules.discord.admin import admin_dashboard
from ..base import API_VERSION

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/admin",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Admin"]
)

@router.get("/console")
async def botlist_admin_console_api(request: Request):
    """API to get raw admin console info"""
    return await admin_dashboard(request) # Just directly render the admin dashboard. It knows what to do

@router.patch("/bots/admin/{bot_id}/state")
async def bot_root_update_api(request: Request, bot_id: int, data: BotStateUpdate, Authorization: str = Header("ROOT_KEY")):
    """Root API to update a bots state. Needs the root key"""
    if not secure_strcmp(Authorization, root_key):
        return abort(401)
    await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", data.state, bot_id)
    return {"done": True, "reason": None, "code": 1000}
