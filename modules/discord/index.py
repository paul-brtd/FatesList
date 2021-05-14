from ..core import *

router = APIRouter(
    tags = ["Index"],
    include_in_schema = False
)

@router.get("/err/err")
async def error():
    return int("haha")

@router.get("/discord")
def reroute_support():
    return RedirectResponse("/fates/support/invite")

# We want to handle any request method to index page
@router.get("/")
@router.post("/")
@router.patch("/")
@router.delete("/")
@router.put("/")
@router.head("/")
async def index_fend(request: Request, response: Response, csrf_protect: CsrfProtect = Depends()):
    return await render_index(request = request, api = False, csrf_protect = csrf_protect)

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
async def vanity_bot_uri(request: Request, bt: BackgroundTasks, vanity: str, csrf_protect: CsrfProtect = Depends()):
    vurl = await vanity_bot(vanity)
    print("Vanity: ", vurl)
    if vurl is None:
        return await templates.e(request, "Invalid Vanity")
    if vurl[1] == "bot":
        return await render_bot(bt = bt, bot_id = vurl[0], request = request, api = False, csrf_protect = csrf_protect)
    else:
        return await templates.e(request, f"This is a {vurl[1]}. This is a work in progress :)", status_code = 400)

@router.get("/{vanity}/edit")
async def vanity_edit(request: Request, vanity: str, bt: BackgroundTasks):
    vurl = await vanity_bot(vanity)
    if vurl is None:
        return await templates.e(request, "Invalid Vanity")
    if vurl[1] == "profile":
        return abort(404)
    eurl = "/".join([site_url, vurl[1], str(vurl[0]), "edit"])
    return RedirectResponse(eurl)

@router.get("/{vanity}/vote")
async def vanity_vote(request: Request, vanity: str):
    vurl = await vanity_bot(vanity)
    if vurl is None:
        return await templates.e(request, "Invalid Vanity")
    if vurl[1] == "profile":
        return abort(404)
    eurl = "/".join([site_url, vurl[1], str(vurl[0]), "vote"])
    return RedirectResponse(eurl)

@router.get("/{vanity}/invite")
async def vanity_invite(request: Request, vanity: str):
    vurl = await vanity_bot(vanity)
    if vurl is None:
        return await templates.e(request, "Invalid Vanity")
    if vurl[1] == "profile":
        return abort(404)
    eurl = "/".join([site_url, vurl[1], str(vurl[0]), "invite"])
    return RedirectResponse(eurl)
@router.get("/v/{a:path}")
async def v_legacy(request: Request, a: str):
    return RedirectResponse(str(request.url).replace("/v/", "/"))

@router.get("/feature/{name}")
async def features_view(request: Request, name: str):
    if name not in features.keys():
        return abort(404)
    bots = await db.fetch("SELECT description, banner, votes, servers, bot_id, invite, state FROM bots, unnest(features) feature WHERE feature = $1 and (state = 0 or state = 6) ORDER BY votes DESC LIMIT 12", name)
    bot_obj = await parse_index_query(bots)
    return await templates.TemplateResponse("feature.html", {"request": request, "name": name, "feature": features[name], "bots": bot_obj})

@router.get("/fates/stats")
async def stats():
    return RedirectResponse("/admin/console?stats=1")

@router.get("/api/docs")
async def api_docs_view(request: Request):
    return RedirectResponse("https://apidocs.fateslist.xyz")

@router.get("/fates/tos")
async def tos_page(request: Request):
    return await templates.TemplateResponse("tos.html", {"request": request})

@router.get("/coins/buy")
async def stripetest(request: Request):
    return await templates.TemplateResponse("coin_buy.html", {"request": request, "stripe_publishable_key": stripe_publishable_key})

