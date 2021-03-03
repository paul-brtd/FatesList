from ..deps import *

router = APIRouter(
    tags = ["Index"],
    include_in_schema = False
)

# We want to handle any request method to index page
@router.get("/")
@router.post("/")
@router.patch("/")
@router.delete("/")
@router.put("/")
@router.head("/")
async def index_fend(request: Request):
    return await render_index(request = request, api = False)

@router.get("/legal")
async def legal_router():
    return RedirectResponse("/static/tos.html", status_code = 303)

@router.get("/etest/{code}")
async def test_error(code: int):
    raise TypeError()

@router.get("/none")
async def nonerouter():
    return RedirectResponse("/static/assets/img/banner.webp", status_code = 301)

@router.get("/{vanity}")
async def vanity_bot_uri(request: Request, vanity: str):
    vurl = await vanity_bot(vanity)
    print("Vanity: ", vurl)
    if vurl is None:
        return templates.e(request, "Invalid Vanity")
    if vurl[1] == "profile":
        return abort(404)
    return RedirectResponse(vurl[0])

@router.get("/{vanity}/edit")
async def vanity_edit(request: Request, vanity: str):
    vurl = await vanity_bot(vanity)
    if vurl is None:
        return templates.e(request, "Invalid Vanity")
    if vurl[1] == "profile":
        return abort(404)
    return RedirectResponse(vurl[0] + "/edit")

@router.get("/{vanity}/vote")
async def vanity_vote(request: Request, vanity: str):
    vurl = await vanity_bot(vanity)
    if vurl is None:
        return templates.e(request, "Invalid Vanity")
    if vurl[1] == "profile":
        return abort(404)
    return RedirectResponse(vurl[0] + "/vote")

@router.get("/{vanity}/invite")
async def vanity_invite(request: Request, vanity: str):
    vurl = await vanity_bot(vanity)
    if vurl is None:
        return templates.e(request, "Invalid Vanity")
    if vurl[1] == "profile":
        return abort(404)
    return RedirectResponse(vurl[0] + "/invite")

@router.get("/v/{a:path}")
async def v_legacy(request: Request, a: str):
    return RedirectResponse(str(request.url).replace("/v/", "/"))

@router.get("/feature/{name}")
async def features_view(request: Request, name: str):
    if name not in features.keys():
        return abort(404)
    feature_bots = (f"SELECT description, banner, certified, votes, servers, bot_id, invite FROM bots WHERE ('{str(name)}' = ANY(features)) and queue = false and banned = false and disabled = false ORDER BY votes DESC;")
    print(feature_bots)
    bots = await db.fetch(feature_bots)
    bot_obj = await parse_bot_list(bots)
    return templates.TemplateResponse("feature.html", {"request": request, "name": name, "feature": features[name], "bots": bot_obj})

@router.get("/fates/stats")
async def stats():
    return RedirectResponse("/admin/console?stats=1")

@router.get("/api/docs")
async def api_docs_view(request: Request):
    return HTMLResponse(open("static/api_docs.html").read())
