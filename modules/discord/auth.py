from ..core import *

router = APIRouter(
    prefix = "/auth",
    tags = ["Auth"],
    include_in_schema = False
)

@router.get("/login")
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

@router.get("/login/confirm")
async def login_confirm(request: Request, code: str, state: str, site_redirect: str):
    if "user_id" in request.session.keys():
        return RedirectResponse("/")
    else:
        async with aiohttp.ClientSession() as sess:
            async with sess.post(f"{site_url}/api/users", json = {
                "code": code, 
                "state": state,
            }) as res:
                json = await res.json()
                if res.status == 400:
                    if not json["banned"]:
                        return await templates.e(request, json["reason"])
                    return await templates.e(request, reason = f"Please note that {json['ban']['desc']}", main=f'You have been {json["ban"]["type"]} banned on Fates List')
     
                request.session["scopes"] = orjson.dumps(json["scopes"]).decode("utf-8")
                request.session["access_token"] = orjson.dumps(json["access_token"]).decode("utf-8")
                request.session["user_id"] = int(json["user"]["id"])
                request.session["username"] = json["user"]["username"]
                request.session["avatar"] = json["user"]["avatar"]
                request.session["user_token"] = json["token"]
                request.session["user_css"] = json["css"]
                request.session["js_allowed"] = json["js_allowed"]
                request.session["site_lang"] = json["site_lang"]
                return HTMLResponse(f"<script>window.location.replace('{site_redirect}')</script>")
            
@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
