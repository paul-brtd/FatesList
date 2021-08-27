from modules.discord.bots import vote_bot_get

from ..core import *
from config import privacy_policy
router = APIRouter(
    tags = ["Index"],
    include_in_schema = False
)

@router.get("/dm/help")
async def exp1(request: Request):
    data = {
        "user_id": request.session.get("user_id"), 
        "logged_in": "user_id" in request.session.keys(),
        "vote_epoch": None,
        "user_agent": request.headers.get("User-Agent"),
        "user": None
    }

    if data["logged_in"]:
        data["vote_epoch"] = await db.fetchval("SELECT vote_epoch FROM users WHERE user_id = $1", data["user_id"])
        data["user"] = await get_user(data["user_id"], worker_session=request.app.state.worker_session)

    return data


@router.get("/discord")
def reroute_support():
    return RedirectResponse("/fates/support/invite")

# We want to handle any request method to index page
@router.get("/")
@router.head("/")
async def index_fend(request: Request, cert: Optional[bool] = True):
    return await render_index(request = request, api = False, cert = cert)

@router.get("/etest/{code}")
async def test_error(code: int):
    if code == 500:
        b = 1 + thisshoulderror
        raise TypeError("Test 500")
    return abort(code)

@router.get("/none")
async def nonerouter():
    return RedirectResponse("/static/assets/img/banner.webp", status_code = 301)

@router.get("/{vanity}")
async def vanity_bot_uri(request: Request, bt: BackgroundTasks, vanity: str):
    vurl = await vanity_bot(vanity)
    logger.trace("Vanity for this object: ", vurl)
    if vurl is None:
        return await templates.e(request, "Invalid Vanity")
    if vurl[1] == "bot":
        return await render_bot(bt = bt, bot_id = vurl[0], request = request, api = False)
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
    if vurl[1] == "bot":
        return await vote_bot_get(request, bot_id = vurl[0])


@router.get("/{vanity}/invite")
async def vanity_invite(request: Request, vanity: str):
    vurl = await vanity_bot(vanity)
    if vurl is None:
        return await templates.e(request, "Invalid Vanity")
    if vurl[1] == "profile":
        return abort(404)
    eurl = "/".join([site_url, vurl[1], str(vurl[0]), "invite"])
    return RedirectResponse(eurl)

@router.get("/feature/{name}")
async def features_view(request: Request, name: str):
    if name not in features.keys():
        return abort(404)
    bots = await db.fetch("SELECT description, banner_card AS banner, votes, guild_count, bot_id, invite, state FROM bots, unnest(features) feature WHERE feature = $1 and (state = 0 or state = 6) ORDER BY votes DESC LIMIT 12", name)
    bot_obj = await parse_index_query(request.app.state.worker_session, bots)
    return await templates.TemplateResponse("feature.html", {"request": request, "name": name, "feature": features[name], "bots": bot_obj})


@router.get("/fates/stats")
async def stats_page(request: Request, full: bool = False):
    worker_session = request.app.state.worker_session
    certified = await do_index_query(state = [enums.BotState.certified], limit = None, worker_session = worker_session) 
    bot_amount = await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    queue = await do_index_query(state = [enums.BotState.pending], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    under_review = await do_index_query(state = [enums.BotState.under_review], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    if full:
        denied = await do_index_query(state = [enums.BotState.denied], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
        banned = await do_index_query(state = [enums.BotState.banned], limit = None, add_query = "ORDER BY created_at ASC", worker_session = worker_session)
    data = {
        "certified": certified,
        "bot_amount": bot_amount,
        "queue": queue,
        "denied": denied if full else [],
        "denied_amt": await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = $1", enums.BotState.denied),
        "banned": banned if full else [],
        "banned_amt": await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = $1", enums.BotState.banned),
        "under_review": under_review,
        "full": full
    }
    if str(request.url.path).startswith("/api"): # Check for API
        return data # Return JSON if so
    return await templates.TemplateResponse("admin.html", {"request": request} | data) # Otherwise, render the template

@router.get("/fates/login")
async def login_get(request: Request, redirect: Optional[str] = None, pretty: Optional[str] = "to access this page"):
    if "user_id" in request.session.keys():
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    return await templates.TemplateResponse(
            "login.html", 
            {
                "request": request
            }, 
            context = {
                "perm_needed": redirect is not None, 
                "perm_pretty": pretty, 
                "redirect": redirect if redirect else '/'
            }
    )

@router.get("/fates/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


@router.get("/api/docs")
async def api_docs_view(request: Request):
    return RedirectResponse("https://apidocs.fateslist.xyz")

@router.get("/fates/tos")
async def tos_page(request: Request):
    return await templates.TemplateResponse("tos.html", {"request": request, "policy": privacy_policy})

@router.get("/fates/rules")
async def rules_page(request: Request):
    return await templates.TemplateResponse("rules.html", {"request": request, "policy": rules})
