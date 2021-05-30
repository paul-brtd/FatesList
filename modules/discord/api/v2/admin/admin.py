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
