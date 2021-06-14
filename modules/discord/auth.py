from ..core import *

router = APIRouter(
    prefix = "/auth",
    tags = ["Auth"],
    include_in_schema = False
)


@router.get("/login")
async def login_get(request: Request, redirect: Optional[str] = None, pretty: Optional[str] = "to access this page", csrf_protect: CsrfProtect = Depends()):
    if redirect:
        if not redirect.startswith("/") and not redirect.startswith("https://fateslist.xyz"):
            return ORJSONResponse({"detail": "Invalid redirect. You may only redirect to pages on Fates List"}, status_code = 400)
    if "user_id" in request.session.keys():
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    return await templates.TemplateResponse("login.html", {"request": request, "perm_needed": redirect is not None, "perm_pretty": pretty, "csrf_protect": csrf_protect, "redirect": redirect if redirect else '/'})

@router.post("/login")
async def login_post(request: Request, redirect: str, join_servers: str = FForm("off"), server_list: str = FForm("off"), csrf_protect: CsrfProtect = Depends()):
    ret = await verify_csrf(request, csrf_protect)
    if ret:
        return ret
    scopes = ["identify"]

    # Join Server
    if join_servers == "on":
        scopes.append("guilds.join")

    # Server Lists
    if server_list == "on":
        scopes.append("guilds")
    async with aiohttp.ClientSession() as sess:
        async with sess.post(f"{site_url}/api/v2/oauth", json = {"redirect": redirect, "scopes": scopes}) as res:
            json = await res.json()
            url = json["url"]
    return RedirectResponse(url, status_code=HTTP_303_SEE_OTHER)

@router.get("/login/confirm")
async def login_confirm(request: Request, code: str, state: str):
    if "user_id" in request.session.keys():
        return RedirectResponse("/")
    else:
        scopes = state.split("|")[0]
        redirect = state.split("|")[1] if len(state.split("|")) >= 2 else "/" 
        async with aiohttp.ClientSession() as sess:
            async with sess.put(f"{site_url}/api/users", json = {"code": code, "scopes": scopes.split(" "), "redirect": redirect}) as res:
                json = await res.json()
                if res.status == 400:
                    if not json["banned"]:
                        return await templates.e(request, json["reason"])
                    return await templates.e(request, reason = f"Please note that {json['ban']['desc']}", main=f'You have been {json["ban"]["type"]} banned on Fates List')
                request.session["state"] = json["state"]
                request.session["access_token"] = json["access_token"]
                request.session["user_id"] = int(json["user"]["id"])
                request.session["username"] = json["user"]["username"]
                request.session["avatar"] = json["user"]["avatar"]
                request.session["user_token"] = json["token"]
                request.session["user_css"] = json["css"]
                request.session["js_allowed"] = json["js_allowed"]
                return HTMLResponse(f"<script>window.location.replace('{redirect}')</script>")

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
