from fastapi import FastAPI, Request, Form
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
import random
import math
import time
import uuid
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from pydantic import BaseModel
from starlette.status import HTTP_302_FOUND, HTTP_303_SEE_OTHER
import secrets
import string
import discord
import asyncio
from discord.ext import commands, tasks
import time
import re
from starlette_wtf import CSRFProtectMiddleware, csrf_protect,StarletteForm
# CONFIG
bot_logs=789946587203764224
reviewing_server=791403194710360064
admin_roles = {"guild":789934742128558080,"bot_review":789941907563216897,"mod":790698030549827594,"admin":790697779068272661,"owner":792181964933038130}
support_url = "https://discord.gg/Ynbf3qqxHV"
TOKEN = "NzkxMzk4MDQ0MDM3MTUyNzc4.X-Ok3Q.6uc4aIzt_HW2ZsW9uNe5C9uAXC8"
TAGS = ["music", "moderation", "economy", "fun", "anime", "games",
        "web_dashboard", "logging", "streams", "game_stats", "leveling", "roleplay"]
# Setup
intent = discord.Intents.all()
client = commands.AutoShardedBot(command_prefix='!', intents=intent)
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="E@Dycude3u8z382")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.add_middleware(CSRFProtectMiddleware, csrf_secret="ADDE-OS39-MA2K-lS09-3K9soI-Iskmd-93829-()(()-2937()K")
# Secret creator


def get_token(length: str) -> str:
    secure_str = "".join(
        (secrets.choice(string.ascii_letters + string.digits)
         for i in range(length))
    )
    return secure_str


async def setup_db():

    db = await asyncpg.create_pool(host="107.152.38.124", port=5432, user="postgres", password="rocco123", database="FatesList")

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
    try:
        bot = client.get_user(int(userid))
        if bot:
            return {"username": str(bot.name), "avatar": str(bot.avatar_url)}
        else:
            return None
    except:
        return None


async def get_user(userid):
    try:
        user = client.get_user(int(userid))
        if user:
            return {"username": str(user), "avatar": str(user.avatar_url)}
        else:
            return None
    except:
        return None


@app.on_event("startup")
async def startup():
    global db
    db = await setup_db()
    asyncio.create_task(client.start(TOKEN))


@client.command()
async def approve(ctx, bot_id: int):
    api_token = get_token(64)
    await db.execute("UPDATE bots SET queue=false,api_token=$1 WHERE bot_id = $2", api_token, bot_id)
    await ctx.send("APPROVED((TESTING))")


@app.get("/")
@csrf_protect
async def home(request: Request):
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false ORDER BY votes DESC LIMIT 12")
    top_voted = []
    # TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            top_voted.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false ORDER BY created_at DESC LIMIT 12")
    new_bots = []
    # new bots
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            new_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false and certified = true LIMIT 12")
    certified_bots = []
    # certified bots
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            certified_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
        # TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: new_tag.capitalize()})

    return templates.TemplateResponse("index.html", {"request": request, "username": request.session.get("username", False), "top_voted": top_voted, "new_bots": new_bots, "certified_bots": certified_bots, "tags_fixed": tags_fixed})


@app.get("/search")
@csrf_protect
async def search(request: Request, q):
    start = time.time()
    fetch = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false and description ~* $1 ORDER BY votes", re.sub(r"\W+|_", " ", q))
    search_bots = []
    # TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            search_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})

        # TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: new_tag.capitalize()})

    end = time.time()
    print(end - start)

    return templates.TemplateResponse("search.html", {"request": request, "username": request.session.get("username", False), "search_bots": search_bots, "tags_fixed": tags_fixed})


@app.get("/tags/{tag_search}")
@csrf_protect
async def tags(request: Request, tag_search):
    if tag_search not in TAGS:
        return RedirectResponse("/")
    fetch = await db.fetch(f"SELECT description, banner,certified,votes,servers,bot_id,tags,invite FROM bots, unnest(tags) a WHERE  lower(a) = '{tag_search}' ORDER BY votes")
    print(fetch)
    search_bots = []
    # TOP VOTED BOTS
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            search_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})

        # TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: new_tag.capitalize()})

    return templates.TemplateResponse("search.html", {"request": request, "username": request.session.get("username", False), "search_bots": search_bots, "tags_fixed": tags_fixed})


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


@app.get("/login")
@csrf_protect
async def login(request: Request):
    if "userid" in request.session.keys():
        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse(Oauth.Oauth.discord_login_url, status_code=HTTP_303_SEE_OTHER)


@app.api_route("/login/confirm")
@csrf_protect
async def login_confirm(request: Request, code=None):
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
            request.session["avatar"] = "https://cdn.discordapp.com/avatars/" + \
                userjson["id"] + "/" + userjson["avatar"]
        else:
            # No avatar in user
            request.session["avatar"] = "https://s3.us-east-1.amazonaws.com/files.tvisha.aws/posts/crm/panel/attachments/1580985653/discord-logo.jpg"
        await Oauth.Oauth.join_user(access_code,userjson["id"])
        if "RedirectResponse" in request.session.keys():
            return RedirectResponse(request.session["RedirectResponse"])
        return RedirectResponse("/")

class Form(StarletteForm):
    pass
@app.api_route("/bot/add", methods=["GET", "POST"])
@csrf_protect
async def add_bot(request: Request):
    if "userid" in request.session.keys():
        if request.method == "GET":
            # TAGS
            tags_fixed = {}
            for tag in TAGS:
                new_tag = tag.replace("_", " ")
                tags_fixed.update({tag: new_tag.capitalize()})
            form = await Form.from_formdata(request)
            return templates.TemplateResponse("add.html", {"request": request, "tags_fixed": tags_fixed, "username": request.session.get("username", False),"form":form})
        else:
            owner_check = await get_user(request.session["userid"])
            if owner_check:
                pass
            else:
                return templates.TemplateResponse("message.html", {"request": request, "message": "You are not in the support server", "username": request.session.get("username", False)})
            data = await request.form()
            form = data
            fetch = await db.fetch("SELECT bot_id FROM bots WHERE bot_id = $1", int(form["bot_id"]))
            if fetch:
                return templates.TemplateResponse("message.html", {"request": request, "message": "Bot already exists.", "username": request.session.get("username", False)})
            if len(form["description"]) > 101:
                return templates.TemplateResponse("message.html", {"request": request, "message": "Short description is too long.", "username": request.session.get("username", False)})
            try:
                bot_object = await client.fetch_user(int(form["bot_id"]))
            except:
                return templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist", "username": request.session.get("username", False)})
            if not bot_object.bot:
                return templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist", "username": request.session.get("username", False)})
            if form["tags"] == "":
                return templates.TemplateResponse("message.html", {"request": request, "message": "You need to select tags for your bot", "username": request.session.get("username", False)})
            selected_tags = form["tags"].split(",")
            for test in selected_tags:
                if test in TAGS:
                    pass
                else:
                    return templates.TemplateResponse("message.html", {"request": request, "message": "One of your bot tags didn't exist internally", "username": request.session.get("username", False)})
            header_list = ["image/gif", "image/png", "image/jpeg", "image/jpg"]
            try:
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(form["banner"]) as response:
                        if response.headers['Content-Type'] in header_list:
                            banner = form["banner"]
            except:
                banner = "none"
            creation = time.time()
            await db.execute("INSERT INTO bots(bot_id,prefix,bot_library,invite,website,banner,discord,long_description,description,tags,owner,extra_owners,votes,servers,shard_count,created_at,queue_username,queue_avatar) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$15,$16,$17)", int(form["bot_id"]), form["prefix"], form["library"], form["invite"], form["website"], banner, form["support"], form["long_description"], form["description"], selected_tags, int(request.session["userid"]), form["extra_owners"], 0, 0, int(creation),bot_object.name,str(bot_object.avatar_url))
            channel = client.get_channel(bot_logs)
            owner=str(request.session["userid"])
            bot_id = form["bot_id"]
            bot_name = str(bot_object)
            await channel.send(f"<@{owner}> added the bot <@{bot_id}>({bot_name}) to queue")
            return templates.TemplateResponse("message.html", {"request": request, "message": "Bot has been added.", "username": request.session.get("username", False)})
    else:
        return RedirectResponse("/")
@app.api_route("/bot/edit/{bot_id}", methods=["GET", "POST"])
@csrf_protect
async def edit(request: Request,bot_id:int):
    if "userid" in request.session.keys():
        check = await db.fetchrow("SELECT owner,extra_owners FROM bots WHERE bot_id = $1", int(bot_id))
        if not check:
            return templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist in our database.", "username": request.session.get("username", False)})
        if check["owner"] == int(request.session["userid"]) or str(request.session["userid"]) in check["extra_owners"]:
            pass
        else:
            return templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot.", "username": request.session.get("username", False)})
        if request.method == "GET":
            fetch = await db.fetchrow("SELECT * FROM bots WHERE bot_id = $1", int(bot_id))
            tags_fixed = {}
            for tag in TAGS:
                new_tag = tag.replace("_", " ")
                tags_fixed.update({tag: new_tag.capitalize()})
            form = await Form.from_formdata(request)
            return templates.TemplateResponse("edit.html", {"request": request, "tags_fixed": tags_fixed, "username": request.session.get("username", False),"fetch":fetch,"form":form})
        else:
            owner_check = await get_user(request.session["userid"])
            if owner_check:
                pass
            else:
                return templates.TemplateResponse("message.html", {"request": request, "message": "You are not in the support server", "username": request.session.get("username", False)})
            data = await request.form()
            form = data
            fetch = await db.fetch("SELECT bot_id FROM bots WHERE bot_id = $1", int(form["bot_id"]))
            if not fetch:
                return templates.TemplateResponse("message.html", {"request": request, "message": "Bot doesn't exist.", "username": request.session.get("username", False)})
            if len(form["description"]) > 101:
                return templates.TemplateResponse("message.html", {"request": request, "message": "Short description is too long.", "username": request.session.get("username", False)})
            if form["tags"] == "":
                return templates.TemplateResponse("message.html", {"request": request, "message": "You need to select tags for your bot", "username": request.session.get("username", False)})
            selected_tags = form["tags"].split(",")
            for test in selected_tags:
                if test in TAGS:
                    pass
                else:
                    return templates.TemplateResponse("message.html", {"request": request, "message": "One of your bot tags didn't exist internally", "username": request.session.get("username", False)})
            header_list = ["image/gif", "image/png", "image/jpeg", "image/jpg"]
            try:
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(form["banner"]) as response:
                        if response.headers['Content-Type'] in header_list:
                            banner = form["banner"]
            except:
                banner = "none"
            creation = time.time()
            await db.execute("UPDATE bots SET bot_id=$1, bot_library=$2, webhook=$3, description=$4, long_description=$5, prefix=$6, website=$7, discord=$8, tags=$9, banner=$10, owner=$11, extra_owners=$12, invite=$13 WHERE bot_id = $14", fetch["bot_id"],form["library"],form["webhook"],form["description"],form["long_description"],form["prefix"],form["website"],form["support"],selected_tags,banner,int(request.session["userid"]),str(form["extra_owners"]),form["invite"],int(bot_id))
            channel = client.get_channel(bot_logs)
            owner=str(request.session["userid"])
            bot_id = form["bot_id"]
            await channel.send(f"<@{owner}> edited the bot <@{bot_id}>")
            return templates.TemplateResponse("message.html", {"request": request, "message": "Bot has been edited.", "username": request.session.get("username", False)})

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

@app.api_route("/admin",methods=["GET","POST"])
async def admin(request:Request,admin=None):
    if "userid" in request.session.keys():
        if request.method == "GET":
            guild = client.get_guild(admin_roles["guild"])
            user = guild.get_member(int(request.session["userid"]))
            users_roles = user.roles#That is a list of ids IHOPE
            user_roles = []
            for role in users_roles:
                user_roles.append(role.id)
            admin = False
            owner=False
            review=False
            mod=False
            print(user_roles)
            if admin_roles["bot_review"] in user_roles:
                review=True
            if admin_roles["mod"] in user_roles:
                mod = True
            if admin_roles["admin"] in user_roles:
                admin = True
            if admin_roles["owner"] in user_roles:
                owner = True
            if mod == False and admin == False and owner == False and review==False:
                return RedirectResponse("/")
            else:
                certified_bots = len(await db.fetch("SELECT bot_id FROM bots WHERE certified = true"))
                bots = len(await db.fetch("SELECT bot_id FROM bots WHERE queue = false"))
                fetch = await db.fetch("SELECT * FROM bots WHERE queue = true") 
                queue_bots = []
                queue_amount = len(fetch)
                    # TOP VOTED BOTS
                for bot in fetch:
                    bot_info = {"username":bot["queue_username"],"avatar":bot["queue_avatar"]}
                    if bot_info:
                        queue_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"]})
                return templates.TemplateResponse("admin.html",{"request":request,"cert":certified_bots,"bots":bots,"queue_bots":queue_bots,"queue_amount":queue_amount,"admin":admin,"mod":mod,"owner":owner,"bot_review":review,"username":request.session["username"]})
        else:
            guild = client.get_guild(admin_roles["guild"])
            user = guild.get_member(int(request.session["userid"]))
            users_roles = user.roles#That is a list of ids IHOPE
            user_roles = []
            for role in users_roles:
                user_roles.append(role.id)

            if admin_roles["owner"] in user_roles:
                pass
            else:
                return RedirectResponse("/")
            if admin=="certify":
                data = await request.form()
                await db.execute("UPDATE bots SET certified = true WHERE bot_id = $1", int(data["bot_id"]))
                channel = client.get_channel(bot_logs)
                bot_id = data["bot_id"]
                owner=str(request.session["userid"])
                await channel.send(f"<@{owner}> certified the bot <@{bot_id}>")
                return templates.TemplateResponse("message.html", {"request": request, "message": "Hey mikes, i hope it certified the bot!", "username": request.session.get("username", False)})
            elif admin=="uncertify":
                data = await request.form()
                await db.execute("UPDATE bots SET certified = false WHERE bot_id = $1", int(data["bot_id"]))   
                channel = client.get_channel(bot_logs)
                bot_id = data["bot_id"]
                owner=str(request.session["userid"])
                await channel.send(f"<@{owner}> uncertified the bot <@{bot_id}>")
                return templates.TemplateResponse("message.html", {"request": request, "message": "Hey mikes, i hope it uncertified the bot!", "username": request.session.get("username", False)})     
            elif admin=="reset": 
                data = await request.form()
                await db.execute("UPDATE bots SET votes = 0")  
                return templates.TemplateResponse("message.html", {"request": request, "message": "Hey mikes, i hope your wish comes true ;)", "username": request.session.get("username", False)})     
    else:
        request.session["RedirectResponse"] = "/admin"
        return RedirectResponse("/login")

@app.get("/description/{bot_id}")
async def bot_desc(request:Request,bot_id):
    bot = await db.fetchrow("SELECT long_description FROM bots WHERE bot_id = $1",int(bot_id))
    if bot:
        return templates.TemplateResponse("description.html",{"request":request,"bot":bot})
    else:
        return "Bot not found! :( Try refreshing. After that either report it on the support server or just continue your day!"
@app.api_route("/admin/review/{bot_id}",methods=["GET","POST"])
async def review(request:Request,bot_id,accept=None,deny=None):
    if "userid" in request.session.keys():
        if request.method == "GET":
            guild = client.get_guild(admin_roles["guild"])
            user = guild.get_member(int(request.session["userid"]))
            users_roles = user.roles#That is a list of ids IHOPE
            user_roles = []
            for role in users_roles:
                user_roles.append(role.id)
            admin = False
            owner=False
            review=False
            mod=False
            print(user_roles)
            if admin_roles["bot_review"] in user_roles:
                review=True
            if admin_roles["mod"] in user_roles:
                mod = True
            if admin_roles["admin"] in user_roles:
                admin = True
            if admin_roles["owner"] in user_roles:
                owner = True
            if mod == False and admin == False and owner == False and review==False:
                return RedirectResponse("/")
            else:
                bot = await db.fetchrow("SELECT * FROM bots WHERE bot_id = $1 and queue=true",int(bot_id))
                if not bot:
                    return templates.TemplateResponse("message.html",{"request":request,"message":"Bot does not exist! Idk how"})
                    # TOP VOTED BOTS
                return templates.TemplateResponse("review.html",{"request":request,"bot":bot,"guild":reviewing_server})
        else:
            guild = client.get_guild(admin_roles["guild"])
            user = guild.get_member(int(request.session["userid"]))
            users_roles = user.roles#That is a list of ids IHOPE
            user_roles = []
            for role in users_roles:
                user_roles.append(role.id)
            admin = False
            owner=False
            review=False
            mod=False
            if admin_roles["bot_review"] in user_roles:
                review=True
            if admin_roles["mod"] in user_roles:
                mod = True
            if admin_roles["admin"] in user_roles:
                admin = True
            if admin_roles["owner"] in user_roles:
                owner = True
            if mod == False and admin == False and owner == False and review==False:
                return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
            else:
                if accept:
                    check = await db.fetchrow("SELECT * FROM bots WHERE bot_id=$1 and queue=true",int(bot_id))
                    if not check:
                        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
                    api_token = get_token(64)
                    await db.execute("UPDATE bots SET queue=false,api_token=$1 WHERE bot_id = $2", api_token, int(bot_id))
                    guild=admin_roles["guild"]
                    return templates.TemplateResponse("last.html",{"request":request,"message":"Bot accepted; You MUST Invite it by this url","username":request.session["username"],"url":f"https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot&guild_id={guild}&disable_guild_select=true&permissions=0"})
                elif deny:
                    #check = await db.fetchrow("SELECT * FROM bots WHERE bot_id=$1 and queue=true",int(bot_id))
                    #if not check:
                        return RedirectResponse("/", status_code=HTTP_303_SEE_OTHER)
                    #channel = client.get_channel(bot_logs)
                    #deny = await db.execute("DELETE FROM bots WHERE bot_id = $1", int(bot_id))
                    #channel = client.get_channel(bot_logs)
                    #bot_id = request.form()["bot_id"]
                    #owner=str(request.session["userid"])
                    #await channel.send(f"<@{owner}> denied the bot <@{bot_id}>")
                    #return templates.TemplateResponse("message.html",{"request":request,"message":"I hope it DENIED the bot review GUY","username":request.session["username"]})
    else:
        request.session["RedirectResponse"] = "/admin"
        return RedirectResponse("/login")
@app.api_route("/admin/review/{bot_id}/deny",methods=["GET","POST"])
async def review_deny(request:Request,bot_id,reason=None):
    pass
@app.api_route("/logout")
@csrf_protect
async def logout(request: Request):
    session = request.session
    session.clear()
    return RedirectResponse("/")
