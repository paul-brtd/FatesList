from fastapi import FastAPI, Request,Form
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import Oauth
import aiohttp
import asyncpg
import json
import os
import datetime
import random, math, time
import uuid
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from pydantic import BaseModel
from starlette.status import HTTP_302_FOUND,HTTP_303_SEE_OTHER
import secrets,string
import discord,asyncio
from discord.ext import commands, tasks
import time,re
#CONFIG
SUPPORT="https://discord.gg/Ynbf3qqxHV"
TOKEN="NzkxMzk4MDQ0MDM3MTUyNzc4.X-Ok3Q.6uc4aIzt_HW2ZsW9uNe5C9uAXC8"
TAGS=["music", "moderation", "economy", "fun", "anime", "games",  "web_dashboard", "logging", "streams", "game_stats", "leveling", "roleplay"]
#Setup
intent = discord.Intents.all()
client = commands.AutoShardedBot(command_prefix = '!', intents=intent)
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="E@Dycude3u8z382")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
#Secret creator

def get_token(length: str) -> str:
    secure_str = "".join(
        (secrets.choice(string.ascii_letters + string.digits) for i in range(length))
    )
    return secure_str

async def setup_db():

    db = await asyncpg.create_pool(host="107.152.38.124", port = 5432, user = "postgres", password = "rocco123", database = "FatesList")

    # some table creation here meow

    return db
async def human_format(num):
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])
async def get_bot(userid):
    bot = client.get_user(int(userid))
    if bot:
        return {"username":str(bot.name), "avatar":str(bot.avatar_url)}
    else:
        return None

async def get_user(userid):
    user = client.get_user(int(userid))
    if user:
        return {"username":str(user), "avatar":str(user.avatar_url)}
    else:
        return None
@app.on_event("startup")
async def startup():
    global db
    db = await setup_db()
    asyncio.create_task(client.start(TOKEN))

@app.get("/")
async def home(request:Request):
    start = time.time()
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id FROM bots WHERE queue = false ORDER BY votes DESC LIMIT 12")
    top_voted = []
    #TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            top_voted.append({"bot":bot,"avatar":bot_info["avatar"],"username":bot_info["username"],"votes":await human_format(bot["votes"]),"servers":await human_format(bot["servers"]),"description":bot["description"]})
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id FROM bots WHERE queue = false ORDER BY created_at DESC LIMIT 12")
    new_bots = []
    #new bots
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            new_bots.append({"bot":bot,"avatar":bot_info["avatar"],"username":bot_info["username"],"votes":await human_format(bot["votes"]),"servers":await human_format(bot["servers"]),"description":bot["description"]})
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id FROM bots WHERE queue = false and certified = true LIMIT 12")
    certified_bots = []
    #certified bots
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            certified_bots.append({"bot":bot,"avatar":bot_info["avatar"],"username":bot_info["username"],"votes":await human_format(bot["votes"]),"servers":await human_format(bot["servers"]),"description":bot["description"]})
        #TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_"," ")
        tags_fixed.update({tag:new_tag.capitalize()})

    print(tags_fixed)
    end = time.time()
    print(end - start)
    return templates.TemplateResponse("index.html", {"request":request, "username":request.session.get("username",False),"top_voted":top_voted,"new_bots":new_bots,"certified_bots":certified_bots,"tags_fixed":tags_fixed})
@app.get("/search")
async def search(request:Request,q):
    start = time.time()
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id FROM bots WHERE description ~* $1 ORDER BY votes",re.sub(r"\W+|_", " ", q))
    search_bots = []
    #TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            search_bots.append({"bot":bot,"avatar":bot_info["avatar"],"username":bot_info["username"],"votes":await human_format(bot["votes"]),"servers":await human_format(bot["servers"]),"description":bot["description"]})
    
    
    
        #TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_"," ")
        tags_fixed.update({tag:new_tag.capitalize()})


    end = time.time()
    print(end - start)

    return templates.TemplateResponse("search.html", {"request":request, "username":request.session.get("username",False),"search_bots":search_bots,"tags_fixed":tags_fixed})

@app.get("/tags/{tag_search}")
async def tags(request:Request,tag_search):
    if tag_search not in TAGS:
        return RedirectResponse("/")
    fetch = await db.fetch(f"SELECT description, banner,certified,votes,servers,bot_id,tags FROM bots, unnest(tags) a WHERE  lower(a) = '{tag_search}' ORDER BY votes")
    print(fetch)
    search_bots = []
    #TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            search_bots.append({"bot":bot,"avatar":bot_info["avatar"],"username":bot_info["username"],"votes":await human_format(bot["votes"]),"servers":await human_format(bot["servers"]),"description":bot["description"]})
    
    
    
        #TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_"," ")
        tags_fixed.update({tag:new_tag.capitalize()})

    return templates.TemplateResponse("search.html", {"request":request, "username":request.session.get("username",False),"search_bots":search_bots,"tags_fixed":tags_fixed})

@app.get("/user/{userid}")
async def user(request:Request,userid):
    user = await get_user(int(userid))
    if not user:
        return RedirectResponse("/")
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id FROM bots WHERE owner = $1 ORDER BY votes",int(userid))
    user_bots = []
    #TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            user_bots.append({"bot":bot,"avatar":bot_info["avatar"],"username":bot_info["username"],"votes":await human_format(bot["votes"]),"servers":await human_format(bot["servers"]),"description":bot["description"]})
    return templates.TemplateResponse("profile.html", {"request":request, "username":request.session.get("username",False),"user_bots":user_bots,"user":user})
@app.get("/support")
async def support(request:Request):
    return RedirectResponse(support)
@app.get("/login")
async def login(request:Request):
    if "userid" in request.session.keys():
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(Oauth.Oauth.discord_login_url,status_code=HTTP_303_SEE_OTHER)

@app.api_route("/login/confirm")
async def login_confirm(request:Request,code=None):
    if "userid" in request.session.keys():
        return RedirectResponse("/")
    else:
        access_code = await Oauth.Oauth.get_access_token(code)
        userjson = await Oauth.Oauth.get_user_json(access_code)
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
            request.session["avatar"] = "https://cdn.discordapp.com/avatars/" + userjson["id"] + "/" + userjson["avatar"]
        else:
            # No avatar in user
            request.session["avatar"] = "https://s3.us-east-1.amazonaws.com/files.tvisha.aws/posts/crm/panel/attachments/1580985653/discord-logo.jpg"
        if "RedirectResponse" in request.session.keys():
            return RedirectResponse(request.session["RedirectResponse"])
        return RedirectResponse("/")


@app.api_route("/logout")
def logout(request:Request):
    session=request.session
    session.clear()
    return RedirectResponse("/")