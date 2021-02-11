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
from discord.ext import commands, tasks
from starlette_wtf import CSRFProtectMiddleware
import builtins
import importlib
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from modules.deps import *
from config import *
import orjson
import os

# Setup
builtins.intent = discord.Intents.all()
builtins.client = commands.AutoShardedBot(command_prefix='!', intents=intent)
builtins.client.PUBAV = {}
builtins.app = FastAPI(default_response_class = ORJSONResponse)
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
        msg = "404\nNot Found"
        code = 404
    elif exc.status_code == 401:
        msg = "401\nNot Authorized"
        code = 401
    elif exc.status_code == 422:
        if url_startswith(request.url, "/bot"):
            msg = "Bot Not Found"
            code = 404
        elif url_startswith(request.url, "/bot"):
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

@client.event
async def on_member_remove(member):
    if member.guild.id == reviewing_server:
        if member.bot:
            channel = client.get_channel(bot_logs)
            bot = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1",member.id)
            if bot is not None:
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
    print("Discord")
    asyncio.create_task(client.start(TOKEN))
    #Verify users and bots!!!

@client.event
async def on_ready():
    print("UP ON DISCORD")

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
