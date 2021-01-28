from fastapi import FastAPI, Request, Form as FForm
from fastapi.exceptions import RequestValidationError
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from prometheusrock import PrometheusMiddleware, metrics_route
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
from ratelimit import RateLimitMiddleware, Rule
from ratelimit.backends.redis import RedisBackend
from ratelimit.auths.ip import client_ip
from config import *

# Setup
builtins.intent = discord.Intents.all()
builtins.client = commands.AutoShardedBot(command_prefix='!', intents=intent)
builtins.app = FastAPI(default_response_class = ORJSONResponse)
builtins.app.add_middleware(SessionMiddleware, secret_key=session_key)
builtins.app.add_middleware(PrometheusMiddleware)
builtins.metrics_key = get_token(128)
builtins.app.add_route("/admin/metrics/" + builtins.metrics_key, metrics_route)
builtins._templates = Jinja2Templates(directory="templates")
builtins.ws_events = [] # events that need to be dispatched
class templates():
    @staticmethod
    def TemplateResponse(f, arg_dict):
        try:
            request = arg_dict["request"]
        except:
            raise KeyError
        status = arg_dict.get("status_code")
        if "userid" in request.session.keys():
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
        arg_dict["mkey"] = builtins.metrics_key
        arg_dict["mobile"] = str(request.url).startswith(mobile_site_url)
        print(arg_dict["mobile"])
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
rb = RedisBackend()
print(rb, type(rb))
builtins.app.add_middleware(ProxyHeadersMiddleware)
builtins.app.add_middleware(
    RateLimitMiddleware,
    authenticate=client_ip,
    backend=rb,
    config={
        "/api/events": [Rule(minute=60), Rule(group="admin")],
        "/api/bb": [Rule(second=300), Rule(group="admin")],
        r"^/": [Rule(minute=120), Rule(group="admin")],
    },
)

def url_startswith(url, begin, slash = True):
    # Slash indicates whether to check /route or /route/
    if slash:
       begin = begin + "/"
    return str(url).startswith(site_url + begin) or str(url).startswith(mobile_site_url + begin)

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
            msg = "Invalid Data Provided\n" + str(exc)
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

@client.event
async def on_ready():
    print("UP ON DISCORD")
    builtins.guild = client.get_guild(reviewing_server)
    builtins.channel = guild.get_channel(bot_logs)

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
