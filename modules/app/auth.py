from ..deps import *

router = APIRouter(
    tags = ["Auth"]
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

        # Create a api token for the user if they do not have one already
        token = await db.fetchrow("SELECT token FROM users WHERE userid = $1", int(userjson["id"]))
        if token is None:
            flag = True
            while flag:
                token = get_token(101)
                tcheck = await db.fetchrow("SELECT token FROM users WHERE token = $1", token)
                if tcheck is None:
                    flag = False
            await db.execute("INSERT INTO users (userid, token, vote_epoch) VALUES ($1, $2, $3)", int(userjson["id"]), token, 0)
        request.session["token"] = token
        if "RedirectResponse" in request.session.keys():
            return RedirectResponse(request.session["RedirectResponse"])
        return RedirectResponse("/")

@router.get("/logout")
@csrf_protect
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
