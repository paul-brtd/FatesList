from ..core import *

router = APIRouter(
    prefix = "/search",
    tags = ["Search"],
    include_in_schema = False
)

@router.get("/t")
async def search(request: Request, q: str):
    return await render_search(request = request, q = q, api = False)

@router.get("/tags")
async def tags(request: Request, tag: str):
    if tag not in TAGS:
        return RedirectResponse("/")
    fetch = await db.fetch(f"SELECT DISTINCT bots.bot_id, bots.description, bots.state, bots.banner, bots.votes, bots.servers, bots.invite FROM bots INNER JOIN bot_tags ON bot_tags.bot_id = bots.bot_id WHERE bot_tags.tag = $1 AND (bots.state = 0 OR bots.state = 6) ORDER BY bots.votes DESC LIMIT 15", tag)
    search_bots = await parse_index_query(fetch)
    return await templates.TemplateResponse("search.html", {"request": request, "username": request.session.get("username", False), "search_bots": search_bots, "tags_fixed": tags_fixed, "avatar": request.session.get("avatar"), "profile_search": False})

@router.get("/profile")
async def profile_search(request: Request, q: Optional[str] = None):
    return await render_profile_search(request = request, q = q, api = False)
