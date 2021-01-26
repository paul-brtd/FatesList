from fastapi import FastAPI, Request, Form as FForm, WebSocket, WebSocketDisconnect
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import Oauth
import aiohttp
import asyncpg
import json
import os
import datetime
import random
import math
import time
import uuid
from pydantic import BaseModel
from starlette.status import HTTP_302_FOUND, HTTP_303_SEE_OTHER
import secrets
import string
import discord
import asyncio
from discord.ext import commands, tasks
from discord.utils import get
import time
import re
from starlette_wtf import CSRFProtectMiddleware, csrf_protect,StarletteForm
import builtins
import importlib
from typing import Tuple
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from modules.deps import *
from ratelimit import RateLimitMiddleware, Rule
from ratelimit.auths import EmptyInformation
from ratelimit.backends.redis import RedisBackend
from ratelimit.auths.ip import client_ip
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from config import *

# Setup
builtins.intent = discord.Intents.all()
builtins.client = commands.AutoShardedBot(command_prefix='!', intents=intent)
builtins.app = FastAPI(default_response_class = ORJSONResponse)
app.add_middleware(SessionMiddleware, secret_key=session_key)
builtins._templates = Jinja2Templates(directory="templates")
builtins.ws_events = [] # events that need to be dispatched
class templates():
    @staticmethod
    def TemplateResponse(f, arg_dict):
        try:
            request = arg_dict["request"]
        except:
            raise KeyError
        if "userid" in request.session.keys():
            if "staff" not in arg_dict.keys():
                guild = client.get_guild(reviewing_server)
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
        return _templates.TemplateResponse(f, arg_dict)
builtins.templates = templates
app.add_middleware(CSRFProtectMiddleware, csrf_secret=csrf_secret)
rb = RedisBackend()
print(rb, type(rb))
app.add_middleware(ProxyHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    authenticate=client_ip,
    backend=rb,
    config={
        "/api/events": [Rule(minute=60), Rule(group="admin")],
        "/api/bb": [Rule(second=300), Rule(group="admin")],
        r"^/": [Rule(minute=120), Rule(group="admin")],
    },
)

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

    db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user="postgres", password=pg_pwd, database="fateslist")

    # some table creation here meow

    return db

@client.event
async def on_member_remove(member):
    if member.guild.id == reviewing_server:
        if member.bot:
            bot = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1",member.id)
            if bot is not None:
                channel = client.get_channel(bot_logs)
                await db.execute("UPDATE bots SET banned = true WHERE bot_id = $1",member.id)
                await channel.send(f"Bot <@{str(member.id)}> {str(member)} has been removed from the server and hence has been banned from the bot list. Contact an admin for more info")
        else:
            bot = await db.fetch("SELECT bot_id FROM bots WHERE owner = $1",member.id)
            if len(bot) >=1:
                for m in bot:
                    await db.execute("UPDATE bots SET banned = true WHERE bot_id = $1",m["bot_id"])
                    await channel.send(f"User <@{str(member.id)}> {str(member)} has been removed from the server and hence his bot <@{str(m['bot_id'])}> been banned from the bot list. Contact an admin for more info")


@app.on_event("startup")
async def startup():
    builtins.db = await setup_db()
    asyncio.create_task(builtins.client.start(TOKEN))
    #Verify users and bots!!!
    rb = RedisBackend()
    print(rb._redis)

@client.command()
async def approve(ctx, bot: discord.Member):
    bot_id = bot.id
    if not ctx.guild:
        return await ctx.send("You must run this command in a guild")
    elif is_staff(builtins.staff_roles, ctx.author.roles, 2)[0]:
        await db.execute("UPDATE bots SET queue=$2 WHERE bot_id = $1", bot_id, False)
        channel = client.get_channel(bot_logs)
        await add_event(int(bot_id), "approve", f"user={str(ctx.author.id)}")
        await channel.send(f"<@{bot_id}> has been approved")
        await ctx.send("Approved this bot :)")
    else:
        await ctx.send("You don't have the permission to do this")

@client.command()
async def deny(ctx, bot: discord.Member, reason: Optional[str] = "There was no reason specified"):
    bot_id = bot.id
    if not ctx.guild:
        return await ctx.send("You must run this command in a guild")
    elif is_staff(builtins.staff_roles, ctx.author.roles, 2)[0]:
        channel = client.get_channel(bot_logs)
        await db.execute("UPDATE bots SET banned = true WHERE bot_id = $1", bot_id)
        channel = client.get_channel(bot_logs)
        await add_event(int(bot_id), "deny", f"user={str(ctx.author.id)}")
        await channel.send(f"<@{str(ctx.author.id)}> denied the bot <@{bot_id}> with the reason: {reason}")
        await ctx.send("MAGA'd this bot :)")
    else:
        await ctx.send("You don't have the permission to do this")
