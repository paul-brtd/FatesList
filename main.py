from fastapi import FastAPI, Request, Form as FForm
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
from modules.deps import *

# CONFIG
builtins.bot_logs=798954080604520509
builtins.reviewing_server=794834630942654546 # Bit of a misnomer, but this is the actual main server
builtins.test_server = 794834630942654546 # And THIS is the test server for reviewing bots
# Confusing right? Sorry, i already did 50% using reviewing server so meow ig
builtins.staff_roles = {
    "guild": {
        "id": 798954276348362782,
        "perm": 1
    }, 
    "bot_review": {
        "id": 798954440132526120,
        "perm": 2
    }, 
    "mod": {
        "id": 798954778042433576, 
        "perm": 3
    },
    "admin": {
        "id": 798954635234508820, 
        "perm": 4,
    },
    "owner": { 
        "id": 798956804511629312,
        "perm": 5
    }
}

builtins.support_url = "https://discord.gg/pUcTnHMSvC"
builtins.TOKEN = "Nzk4OTUxNTY2NjM0Nzc4NjQx.X_8foQ.r3oWyE87FQAXx-Kf5ueyGfzDui4"
builtins.TAGS = ["music", "moderation", "economy", "fun", "anime", "games",
        "web_dashboard", "logging", "streams", "game_stats", "leveling", "roleplay"]
# Setup
builtins.intent = discord.Intents.all()
builtins.client = commands.AutoShardedBot(command_prefix='!', intents=intent)
builtins.app = FastAPI(default_response_class = ORJSONResponse)
app.add_middleware(SessionMiddleware, secret_key="E@Dycude3u8z382")
app.mount("/static", StaticFiles(directory="static"), name="static")
builtins.templates = Jinja2Templates(directory="templates")
app.add_middleware(CSRFProtectMiddleware, csrf_secret="ADDE-OS39-MA2K-lS09-3K9soI-Iskmd-93829-()(()-2937()K")
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

    db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user="rootspring", password="Rootspring11,", database="fateslist")

    # some table creation here meow

    return db

@client.event
async def on_member_remove(member):
    if member.guild.id == admin_roles["guild"]:
        if member.bot:
            bot = await db.fetchone("SELECT * FROM bots WHERE bot_id = $1",member.id)
            if bot:
                await db.execute("DELETE FROM bots WHERE bot_id = $1",member.id)
        else:
            bot = await db.fetch("SELECT * FROM bots WHERE owner = $1",member.id)
            if len(bot) >=1:
                for m in bot:
                    await db.execute("DELETE FROM bots WHERE bot_id = $1",m["bot_id"])

@app.on_event("startup")
async def startup():
    builtins.db = await setup_db()
    asyncio.create_task(builtins.client.start(TOKEN))
    #Verify users and bots!!!


@client.command()
async def approve(ctx, bot_id: int):
    api_token = get_token(64)
    if not ctx.guild:
        return await ctx.send("You must run this command in a guild")
    elif is_staff(builtins.staff_roles, ctx.author.roles, 2)[0]:
        await db.execute("UPDATE bots SET queue=$3, api_token=$1 WHERE bot_id = $2", api_token, bot_id, False)
        channel = client.get_channel(bot_logs)
        await channel.send(f"<@{bot_id}> has been approved")
        await ctx.send("Approved this bot :)")
    else:
        await ctx.send("You don't have the permission to do this")

@app.get("/user/{userid}")
@csrf_protect
async def user(request: Request, userid):
    user = await get_user(int(userid))
    if not user:
        return RedirectResponse("/")
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE owner = $1 and queue = false ORDER BY votes", int(userid))
    user_bots = []
    # TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            user_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
    return templates.TemplateResponse("profile.html", {"request": request, "username": request.session.get("username", False), "user_bots": user_bots, "user": user})


@app.get("/support")
@csrf_protect
async def support(request: Request):
    return RedirectResponse(support_url)

@app.get("/profile")
@csrf_protect
async def profile(request:Request):
    if "userid" in request.session.keys():
        user = await get_user(int(request.session["userid"]))
        if not user:
            return RedirectResponse("/")
        userid = request.session["userid"]
        fetch = await db.fetch("SELECT description,banner,certified,votes,servers,bot_id,invite FROM bots WHERE owner = $1 and queue = false ORDER BY votes", int(userid))
        user_bots = []
        # TOP VOTED BOTS
        for bot in fetch:
            bot_info = await get_bot(bot["bot_id"])
            if bot_info:
                user_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
        fetch = await db.fetch("SELECT description,banner,certified,votes,servers,bot_id,invite,queue_avatar,queue_username FROM bots WHERE owner = $1 and queue = true", int(userid)) 
        queue_bots = []
        # TOP VOTED BOTS
        for bot in fetch:
            bot_info = {"username":bot["queue_username"],"avatar":bot["queue_avatar"]}
            if bot_info:
                queue_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"],"queue_bots":queue_bots})
        return templates.TemplateResponse("profile_personal.html", {"request": request, "username": request.session.get("username", False), "user_bots": user_bots, "user": user,"queue_bots":queue_bots})
    else:
        return RedirectResponse("/")

@app.get("/description/{bot_id}")
async def bot_desc(request:Request,bot_id):
    bot = await db.fetchrow("SELECT long_description FROM bots WHERE bot_id = $1",int(bot_id))
    if bot:
        return templates.TemplateResponse("description.html",{"request":request,"bot":bot})
    else:
        return "Bot not found! :( Try refreshing. After that either report it on the support server or just continue your day!"

