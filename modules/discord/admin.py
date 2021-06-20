from ..core import *

router = APIRouter(
    prefix = "/admin",
    tags = ["Admin"],
    include_in_schema = False
)    

@router.get("/console")
async def admin_dashboard(request: Request):
    certified = await do_index_query(state = [enums.BotState.certified], limit = None) # State 0 and state 6 are approved and certified
    bot_amount = await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    queue = await do_index_query(state = [enums.BotState.pending], limit = None, add_query = "ORDER BY created_at ASC")
    under_review = await do_index_query(state = [enums.BotState.under_review], limit = None, add_query = "ORDER BY created_at ASC")
    denied = await do_index_query(state = [enums.BotState.denied], limit = None, add_query = "ORDER BY created_at ASC")
    banned = await do_index_query(state = [enums.BotState.banned], limit = None, add_query = "ORDER BY created_at ASC")
    data = {
        "certified": certified,
        "bot_amount": bot_amount,
        "queue": queue,
        "denied": denied,
        "banned": banned,
        "under_review": under_review,
    }
    if str(request.url.path).startswith("/api"): # Check for API
        return data # Return JSON if so
    return await templates.TemplateResponse("admin.html", {"request": request} | data) # Otherwise, render the template
