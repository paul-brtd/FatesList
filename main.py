import uvloop
uvloop.install()
from fastapi import FastAPI, Request, Form as FForm
from fastapi.openapi.utils import get_openapi
from starlette_session import SessionMiddleware
from starlette_session.backends import BackendType
from fastapi.responses import ORJSONResponse
from fastapi.templating import Jinja2Templates
import asyncpg
from pydantic import BaseModel
import discord
import asyncio
from starlette_wtf import CSRFProtectMiddleware
import builtins
import importlib
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from modules.core import *
from config import *
import os
from fastapi_limiter import FastAPILimiter
import logging
from starlette.datastructures import URL
from http import HTTPStatus
from copy import deepcopy
from starlette.routing import Mount
import sentry_sdk
from starlette.requests import ClientDisconnect
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
import time

builtins.boot_time = time.time()

sentry_sdk.init(sentry_dsn)
# Setup Bots

# Main Bot

intent_main = discord.Intents.default()
intent_main.typing = False
intent_main.bans = False
intent_main.emojis = False
intent_main.integrations = False
intent_main.webhooks = False
intent_main.invites = False
intent_main.voice_states = False
intent_main.messages = False
intent_main.members = True
intent_main.presences = True
builtins.client = discord.Client(intents=intent_main)

# Server Bot

intent_server = deepcopy(intent_main)
intent_server.presences = False
builtins.client_servers = discord.Client(intents=intent_server)


# Setup FastAPI with required urls and orjson for faster json handling
app = FastAPI(default_response_class = ORJSONResponse, redoc_url = "/api/docs/redoc", docs_url = "/api/docs/swagger", openapi_url = "/api/docs/openapi")

# Add Sentry
app.add_middleware(SentryAsgiMiddleware)

# Setup CSRF protection
app.add_middleware(CSRFProtectMiddleware, csrf_secret=csrf_secret)

# Middleware to proxy uvicorn IP addresses
app.add_middleware(ProxyHeadersMiddleware)

# Setup exception handling
@app.exception_handler(401)
@app.exception_handler(403)
@app.exception_handler(404)
@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
@app.exception_handler(500)
@app.exception_handler(HTTPException)
@app.exception_handler(Exception)
async def validation_exception_handler(request, exc):
    return await WebError.error_handler(request, exc)

print("Loading discord modules for Fates List")

# Include all the modules by looping through and using importlib to import them and then including them in fastapi
for f in os.listdir("modules/discord"):
    if not f.startswith("_") or f.startswith("."):
        path = "modules.discord." + f.replace(".py", "")
        print("Discord: Loading " + f.replace(".py", "") + " with path " + path)
        route = importlib.import_module(path)
        app.include_router(route.router)

print("All discord modules have loaded successfully!")

async def setup_db():
    """Function to setup the asyncpg connection pool"""
    db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    return db

@app.on_event("startup")
async def startup():
    """
    On startup:
        - Initialize the database
        - Get bot and server tags
        - Start the main and server bots using tokens in config_secrets.py
        - Sleep for 4 seconds to ensure connections are made before application startup
        - Setup Redis and initialize the ratelimiter and caching system
        - Connect robustly to rabbitmq for add bot/edit bot/delete bot
    """
    builtins.up = False

    builtins.db = await setup_db()

    # Set bot tags
    tags_db = await db.fetch("SELECT id, icon FROM bot_list_tags WHERE type = 0 or type = 2")
    tags =  {}
    for tag in tags_db:
        tags = tags | {tag["id"]: tag["icon"]}
    builtins.tags_fixed = calc_tags(tags)
    builtins.TAGS = tags

    print("Discord init beginning")
    asyncio.create_task(client.start(TOKEN_MAIN))
    asyncio.create_task(client_servers.start(TOKEN_SERVER))
    await asyncio.sleep(4)
    builtins.redis_db = await aioredis.from_url('redis://localhost', db = 1)
    app.add_middleware(SessionMiddleware, backend_type = BackendType.aioRedis, backend_client = redis_db, secret_key=session_key, https_only = True, max_age = 60*60*12, cookie_name = "session") # 1 day expiry cookie
    FastAPILimiter.init(redis_db, identifier = rl_key_func)
    builtins.rabbitmq_db = await aio_pika.connect_robust(
        f"amqp://fateslist:{rabbitmq_pwd}@127.0.0.1/"
    )
    builtins.up = True

@app.on_event("shutdown")
async def close():
    """Close all commections on shutdown"""
    print("Closing")
    await redis_db.close()
    await rabbitmq_db.close()
    await db.close()

# Two events to let us know when discord.py is up and ready
@client.event
async def on_ready():
    print(client.user, "up")

@client_servers.event
async def on_ready():
    print(client_servers.user, "up [SERVER BOT]")

def calc_tags(TAGS):
    # Tag calculation
    tags_fixed = []
    for tag in TAGS.keys():
        # For every key in tag dict, create the "fixed" tag information (friendly and easy to use data for tags)
        tags_fixed.append({"name": tag.replace("_", " ").title(), "iconify_data": TAGS[tag], "id": tag})
    return tags_fixed

builtins.server_tags_fixed = []
for tag in SERVER_TAGS.keys():
    server_tags_fixed.append({"name": tag.replace("_", " ").title(), "iconify_data": SERVER_TAGS[tag], "id": tag})

# Two variables used in our logger
BOLD_START =  "\033[1m"
BOLD_END = "\033[0m"

@app.middleware("http")
async def fateslist_request_handler(request: Request, call_next):
    """
        Simple middleware to:
            - Handle API version and internally redirect by changing ASGI scope at request.scope
            - Transparently redirect /bots to /bot and /servers to /servers/index by changing ASGI scope (no 303 since thats bad UX)
            - Set and record the process time for analytics
    """
    if str(request.url.path).startswith("/bots/"):
        request.scope["path"] = str(request.url.path).replace("/bots", "/bot", 1)
    if str(request.url.path) in ["/servers/", "/servers"]:
        request.scope["path"] = "/servers/index"
    request.scope, api_ver = version_scope(request, 2) # Transparently redirect /api to /api/vX excluding docs and already /api/vX'd apis
    start_time = time.time() # Get process time start
    try:
        response = await asyncio.shield(call_next(request)) # Process request
    except ClientDisconnect:
        try:
            request._is_disconnected = False
        except:
            print("Disconnected")
        response = await asyncio.shield(call_next(request))
    process_time = time.time() - start_time # Get time taken
    response.headers["X-Process-Time"] = str(process_time) # Record time taken
    response.headers["FL-API-Version"] = api_ver # Record currently used api version for debug
    # Fuck CORS
    response.headers["Access-Control-Allow-Origin"] = request.headers.get('Origin') if request.headers.get('Origin') else "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    # Gunicorn logging is trash, lets fix that with custom logging
    query_str = f'?{request.scope["query_string"].decode("utf-8")}' if request.scope["query_string"] else "" # Get query strings
    print(f"{request.client.host} - {BOLD_START}{request.method} {request.url.path}{query_str} HTTP/{request.scope['http_version']} - {response.status_code} {HTTPStatus(response.status_code).phrase}{BOLD_END}") # Print logs like uvicorn
    return response # Return response to user

def fl_openapi():
    """Custom OpenAPI description"""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Fates List",
        version="1.0",
        description="Only v2 beta 2 API is supported (v1 is the old one that fateslist.js currently uses). The default API is v2. This means /api will point to this. To pin a api, either use the FL-API-Version header or directly use /api/v/{version}.",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = fl_openapi # OpenAPI schema setup

