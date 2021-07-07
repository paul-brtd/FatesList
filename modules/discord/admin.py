from ..core import *

router = APIRouter(
    prefix = "/admin",
    tags = ["Admin"],
    include_in_schema = False
)    

@router.get("/console")
async def admin_dashboard(request: Request):
    worker_session = request.app.state.worker_session
    certified = await do_index_query(state = [enums.BotState.certified], limit = None, worker_session = worker_session) 
    bot_amount = await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    queue = await do_index_query(state = [enums.BotState.pending], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    under_review = await do_index_query(state = [enums.BotState.under_review], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    denied = await do_index_query(state = [enums.BotState.denied], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    banned = await do_index_query(state = [enums.BotState.banned], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
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
