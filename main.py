from fastapi import FastAPI, Request, Form as FForm
from starlette.middleware.sessions import SessionMiddleware
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
from modules.deps import *
from config import *
import orjson
import os
import aioredis

# Setup
intent = discord.Intents.all()
builtins.client = discord.Client(intents=intent)

app = FastAPI(default_response_class = ORJSONResponse, docs_url = None, redoc_url = "/api/docs")
app.add_middleware(SessionMiddleware, secret_key=session_key)

app.add_middleware(CSRFProtectMiddleware, csrf_secret=csrf_secret)
app.add_middleware(ProxyHeadersMiddleware)

@app.exception_handler(401)
@app.exception_handler(404)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return await FLError.error_handler(request, exc)

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
    asyncio.create_task(client.start(TOKEN_MAIN))
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
