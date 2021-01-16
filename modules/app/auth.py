from ..deps import *

router = APIRouter(
    tags = ["Auth"],
    include_in_schema = False
)

@router.get("/login")
@csrf_protect
async def login(request: Request):
    if "userid" in request.session.keys():
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(discord_o.discord_login_url, status_code=HTTP_303_SEE_OTHER)

@router.get("/login/confirm")
@csrf_protect
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
        await discord_o.join_user(access_code,userjson["id"])
        token = await get_user_token(int(userjson["id"]))
        request.session["token"] = token
        if "RedirectResponse" in request.session.keys():
            return RedirectResponse(request.session["RedirectResponse"])
        return RedirectResponse("/")

@router.get("/logout")
@csrf_protect
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
