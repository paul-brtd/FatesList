from ..deps import *

router = APIRouter(
    prefix = "/auth",
    tags = ["Auth"],
    include_in_schema = False
)

discord_o = Oauth()

@router.get("/login")
async def login_get(request: Request, redirect: Optional[str] = None, pretty: Optional[str] = "to access this page"):
    if "userid" in request.session.keys():
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    request.session["redirect"] = redirect
    return templates.TemplateResponse("login.html", {"request": request, "form": await Form.from_formdata(request), "perm_needed": redirect is not None, "perm_pretty": pretty})

@router.post("/login")
@csrf_protect
async def login_post(request: Request, join_servers: str = FForm("off")):
    if join_servers == "off":
        request.session["join_servers"] = False
        return RedirectResponse(discord_o.discord_login_url + discord_o.scope, status_code=HTTP_303_SEE_OTHER)
    else:
        request.session["join_servers"] = True
        return RedirectResponse(discord_o.discord_login_url + discord_o.scope_js, status_code=HTTP_303_SEE_OTHER)

@router.get("/login/confirm")
async def login_confirm(request: Request, code: str):
    if "userid" in request.session.keys():
        return RedirectResponse("/")
    else:
        access_code = await discord_o.get_access_token(code)
        userjson = await discord_o.get_user_json(access_code)
        if userjson["id"]:
            pass
        else:
            return RedirectResponse("/")
        request.session["code"] = access_code
        request.session["userid"] = userjson["id"]
        print(userjson)
        request.session["username"] = str(userjson["name"])
        if (userjson.get("avatar")):
            print("Got avatar")
            request.session["avatar"] = "https://cdn.discordapp.com/avatars/" + \
                userjson["id"] + "/" + userjson["avatar"]
        else:
            # No avatar in user
            request.session["avatar"] = "https://s3.us-east-1.amazonaws.com/files.tvisha.aws/posts/crm/panel/attachments/1580985653/discord-logo.jpg"
        # 794834630942654546
        token = await get_user_token(int(userjson["id"]), request.session.get("username"))
        request.session["token"] = token
        user_css = await db.fetchrow("SELECT css FROM users WHERE user_id = $1", int(request.session["userid"]))
        try:
            request.session["staff"] = is_staff(staff_roles, client.get_guild(main_server).get_member(int(request.session["userid"])).roles, 2)
        except:
            pass # Skip staff check on error
        if user_css is None:
            request.session["user_css"] = ""
        else:
            request.session["user_css"] = user_css["css"]
        if request.session.get("join_servers"):
            await discord_o.join_user(access_code, userjson["id"])
        if request.session.get("redirect") is not None:
            return RedirectResponse(request.session["redirect"])
        return RedirectResponse("/")

@router.get("/logout")
@csrf_protect
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
