from fastapi import FastAPI, Request, Form as FForm
from fastapi.exceptions import RequestValidationError
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
import Oauth
import asyncpg
from pydantic import BaseModel
import discord
import asyncio
from starlette_wtf import CSRFProtectMiddleware
import builtins
import importlib
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from modules.deps import *
from config import *
import orjson
import os
import aioredis

# Setup
builtins.intent = discord.Intents.all()
builtins.client = discord.AutoShardedClient(intents=intent)
builtins.client.PUBAV = {}
builtins.app = FastAPI(default_response_class = ORJSONResponse, docs_url = None, redoc_url = "/api/docs")
builtins.app.add_middleware(SessionMiddleware, secret_key=session_key)
builtins._templates = Jinja2Templates(directory="templates")
builtins.ws_events = [] # events that need to be dispatched
class templates():
    @staticmethod
    def TemplateResponse(f, arg_dict):
        guild = client.get_guild(reviewing_server)
        try:
            request = arg_dict["request"]
        except:
            raise KeyError
        status = arg_dict.get("status_code")
        if "userid" in request.session.keys():
            arg_dict["css"] = request.session.get("user_css")
            if "staff" not in arg_dict.keys():
                user = guild.get_member(int(request.session["userid"]))
                if user is not None:
                    staff = is_staff(staff_roles, user.roles, 2)
                else:
                    staff = [False]
                arg_dict["avatar"] = request.session.get("avatar")
                arg_dict["username"] = request.session.get("username")
        else:
            staff = [False]
        arg_dict["staff"] = staff
        arg_dict["site_url"] = site_url
        if status is None:
            return _templates.TemplateResponse(f, arg_dict)
        return _templates.TemplateResponse(f, arg_dict, status_code = status)

    @staticmethod
    def error(f, arg_dict, status_code):
        arg_dict["status_code"] = status_code
        return templates.TemplateResponse(f, arg_dict)

    @staticmethod
    def e(request, reason: str, status_code: str = 404):
        return templates.error("message.html", {"request": request, "context": reason}, status_code)

builtins.templates = templates
builtins.app.add_middleware(CSRFProtectMiddleware, csrf_secret=csrf_secret)
builtins.app.add_middleware(ProxyHeadersMiddleware)

def url_startswith(url, begin, slash = True):
    # Slash indicates whether to check /route or /route/
    if slash:
       begin = begin + "/"
    return str(url).startswith(site_url + begin)

@builtins.app.exception_handler(401)
@builtins.app.exception_handler(404)
@builtins.app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(request.url)
    if type(exc) == RequestValidationError:
        exc.status_code = 422
    if exc.status_code == 404:
        if url_startswith(request.url, "/bot"):
            msg = "Bot Not Found"
            code = 404
        elif url_startswith(request.url, "/profile"):
            msg = "Profile Not Found"
            code = 404
        else:
            msg = "404\nNot Found"
            code = 404
    elif exc.status_code == 401:
        msg = "401\nNot Authorized"
        code = 401
    elif exc.status_code == 422:
        if url_startswith(request.url, "/bot"):
            msg = "Bot Not Found"
            code = 404
        elif url_startswith(request.url, "/profile"):
            msg = "Profile Not Found"
            code = 404
        else:
            msg = "Invalid Data Provided<br/>" + str(exc)
            code = 422

    json = url_startswith(request.url, "/api")
    if json:
        if exc.status_code == 404 or exc.status_code == 401:
            return await http_exception_handler(request, exc)
        elif exc.status_code == 422:
            return await request_validation_exception_handler(request, exc)
        else:
            pass
    return templates.e(request, msg, code)

app = builtins.app # As much as i hate it, patch uvicorns stupidity

builtins.discord_o = Oauth.Oauth()

print("FATES LIST: Loading Modules")
# Include all the modules
for f in os.listdir("modules/app"):
    if not f.startswith("_"):
        print("APP MODLOAD: modules.app." + f.replace(".py", ""))
        route = importlib.import_module("modules.app." + f.replace(".py", ""))
        app.include_router(route.router)

async def setup_db():

    db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    # some table creation here meow

    return db

@app.on_event("startup")
async def startup():
    builtins.db = await setup_db()
    print("Discord")
    asyncio.create_task(client.start(TOKEN))
    builtins.redis_db = await aioredis.create_redis_pool('redis://localhost')

@app.on_event("shutdown")
async def close():
    print("Closing")
    redis_db.close()
    await redis_db.wait_closed()

@client.event
async def on_ready():
    print("UP ON DISCORD")

# Tag calculation
builtins.tags_fixed = {}
for tag in TAGS.keys():
    tag_icon = TAGS[tag]
    new_tag = tag.replace("_", " ")
    builtins.tags_fixed.update({tag: [new_tag.capitalize(), tag_icon]})
