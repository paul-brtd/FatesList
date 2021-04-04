from ..deps import *

router = APIRouter(
    prefix = "/search",
    tags = ["Search"],
    include_in_schema = False
)

@router.get("/t")
async def search(request: Request, q: str):
    return await render_search(request = request, q = q, api = False)

@router.get("/tags")
@csrf_protect
async def tags(request: Request, tag: str):
    if tag not in TAGS:
        return RedirectResponse("/")
    fetch = await db.fetch(f"SELECT description, banner,certified,votes,servers,bot_id,tags,invite FROM bots, unnest(tags) a WHERE  lower(a) = '{tag}' AND queue = false and banned = false and disabled = false ORDER BY votes DESC LIMIT 12")
    search_bots = await parse_bot_list(fetch)
    return await templates.TemplateResponse("search.html", {"request": request, "username": request.session.get("username", False), "search_bots": search_bots, "tags_fixed": tags_fixed, "avatar": request.session.get("avatar"), "profile_search": False})

@router.get("/profile")
async def profile_search(request: Request, q: Optional[str] = None):
    return await render_profile_search(request = request, q = q, api = False)
