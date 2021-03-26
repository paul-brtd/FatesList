from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, ORJSONResponse
from fastapi.templating import Jinja2Templates
import config
import modules.Oauth as Oauth
from starlette.middleware.sessions import SessionMiddleware
import requests

discord_o = Oauth.Oauth(config.ULAOauthConfig)

templates = Jinja2Templates(directory = "ula/frontend/templates")

app = FastAPI(include_in_schema = False, docs_url = None, redoc_url = None)
app.add_middleware(SessionMiddleware, secret_key = config.ula_session_key)

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "username": request.session.get("username"), "disc": request.session.get("disc"), "api_url": config.ula_api_url})

@app.get("/add_list")
def add_list_route(request: Request):
    return templates.TemplateResponse("add_list.html", {"request": request, "username": request.session.get("username"), "disc": request.session.get("disc"), "userid": request.session.get("userid"), "api_url": config.ula_api_url, "api_token": request.session.get("api_token")})

@app.get("/list/{url}")
def list_render(request: Request, url: str):
    return templates.TemplateResponse("list.html", {"request": request, "username": request.session.get("username"), "disc": request.session.get("disc"), "userid": request.session.get("userid"), "url": url, "api_url": config.ula_api_url})

@app.get("/login")
def login(request: Request):
    oauth = discord_o.get_discord_oauth('identify')
    request.session["state"] = oauth["state"]
    return RedirectResponse(oauth["url"])

@app.get("/login/confirm")
async def confirm_login(request: Request, code: str, state: str):
    if "userid" in request.session.keys():
        return RedirectResponse("https://ula.fateslist.xyz")
    else:
        # Validate the state first
        if request.session.get("state") != state:
            return ORJSONResponse({"detail": "Invalid State"}, status_code = 400)
    try:
        del request.session["state"]
    except:
        pass
    access_token = await discord_o.get_access_token(code, ['identify',])
    request.session["access_token"] = access_token
    userjson = requests.get(config.ula_api_url + f"/login?access_token={access_token['access_token']}")
    if userjson.status_code == 400:
        return ORJSONResponse(userjson.json(), status_code = 400)
    userjson = userjson.json()
    request.session["userid"] = userjson["id"]
    print(userjson)
    request.session["api_token"] = userjson["api_token"]
    request.session["disc"] = userjson["dash"]
    request.session["username"] = str(userjson["name"])
    if userjson.get("avatar"):
        request.session["avatar"] = "https://cdn.discordapp.com/avatars/" + \
        userjson["id"] + "/" + userjson["avatar"]
    else:
        # No avatar in user
        request.session["avatar"] = "https://s3.us-east-1.amazonaws.com/files.tvisha.aws/posts/crm/panel/attachments/1580985653/discord-logo.jpg"
    return RedirectResponse("https://ula.fateslist.xyz")

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
