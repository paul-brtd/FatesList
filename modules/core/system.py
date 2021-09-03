"""Fates List System Bootstrapper"""
import sys
sys.pycache_prefix = "data/pycache"

import asyncio
import builtins
import datetime
import importlib
import os
import signal
import time
import uuid
from http import HTTPStatus

import aio_pika
import aioredis
import asyncpg
import discord
import sentry_sdk
from discord.ext import commands
from fastapi.exceptions import (HTTPException, RequestValidationError,
                                ValidationError)
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from lynxfall.core.classes import Singleton
from lynxfall.oauth.models import OauthConfig
from lynxfall.oauth.providers.discord import DiscordOauth
from lynxfall.ratelimits import LynxfallLimiter
from lynxfall.utils.fastapi import api_versioner, include_routers
from prometheus_client import start_http_server
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from config import (API_VERSION, TOKEN_DBG, TOKEN_MAIN, TOKEN_SERVER,
                    bot_dev_role, bots_role, discord_client_id,
                    discord_client_secret, discord_redirect_uri, lynxfall_key,
                    owner, sentry_dsn, session_key, site, worker_key)
from config._logger import logger
from modules.core.error import WebError
from modules.models import enums
from modules.core.ipc import redis_ipc, redis_ipc_new

from .ratelimits import rl_key_func


class FatesListRequestHandler(BaseHTTPMiddleware):
    """Request Handler for Fates List"""
    def __init__(self, app, *, exc_handler):
        super().__init__(app)
        self.exc_handler = exc_handler
        
        # Methods that should be allowed by CORS
        self.cors_allowed = "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS"
    
        # Default response
        self.default_res = HTMLResponse(
            "Something happened!", 
            status_code=500
        ) 
    
    @staticmethod
    def _log_req(path, request, response):
        """Logs HTTP requests to console (and file)"""
        code = response.status_code
        phrase = HTTPStatus(response.status_code).phrase
        query_str_raw = request.scope["query_string"]

        if query_str_raw:
            query_str = f'?{query_str_raw.decode("utf-8")}'
        else:
            query_str = ""
            
        logger.info(
            f"{request.method} {path}{query_str} | {code} {phrase}"
        )
        
    async def dispatch(self, request, call_next):
        """Run _dispatch, if that fails, log error and do exc handler"""
        request.state.error_id = str(uuid.uuid4())
        request.state.curr_time = str(datetime.datetime.now())
        path = request.scope["path"]
        
        if not request.app.state.ipc_up:
            # This middleware does not apply
            return await call_next(request)

        try:
            res = await self._dispatcher(path, request, call_next)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Site Error Occurred") 
            res = await self.exc_handler(request, exc, log=True)
        
        self._log_req(path, request, res)
        return res if res else self.default_res
    
    async def _dispatcher(self, path, request, call_next):
        """Actual middleware"""
        if request.app.state.worker_session.dying:
            return HTMLResponse("Fates List is going down for a reboot")
        
        logger.trace(request.headers.get("X-Forwarded-For"))
        
        if path.startswith("/bots/"):
            path = path.replace("/bots", "/bot", 1)
        
        # These are checks path should not start with
        is_api = path.startswith("/api")
        request.scope["path"] = path
        
        if is_api:
            # Handle /api as /api/vX excluding docs + pinned requests
            request.scope, api_ver = api_versioner(request, API_VERSION)
    
        start_time = time.time()
        
        # Process request with retry
        try:
            response = await call_next(request)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Site Error Occurred")
            response = await self.exc_handler(request, exc)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        if is_api:
            response.headers["X-API-Version"] = api_ver
    
        # Fuck CORS by force setting headers with proper origin
        origin = request.headers.get('Origin')

        # Make commonly repepated headers shorter
        acac = "Access-Control-Allow-Credentials"
        acao = "Access-Control-Allow-Origin"
        acam = "Access-Control-Allow-Methods"

        response.headers[acao] = origin if origin else "*"
        
        if is_api and origin:
            response.headers[acac] = "true"
        else:
            response.headers[acac] = "false"
        
        response.headers[acam] = self.cors_allowed
        if response.status_code == 405:
            if request.method == "OPTIONS" and is_api:
                response.status_code = 204
                response.headers["Allow"] = self.cors_allowed
       
        return response


class FatesDebugBot(commands.Bot):
    """Fates List Debug Bot"""
    def __init__(self, *, intents):
        self.ready = False
        super().__init__(
            command_prefix=commands.when_mentioned_or('fl!'), intents=intents)

    async def is_owner(self, user: discord.User):
        """Owner check patch"""
        if user.id == owner or user.id in (683530527239962627, 744825560034705508):
            return True
        return False

    async def on_ready(self):
        """on_ready patch"""
        self.ready = True
        logger.success(
            f"{self.user} (DEBUG BOT) should now be up on first worker"
        )

        
class FatesBot(discord.Client):
    """Fates List Regular Bot"""
    def __init__(self, *, intents):
        self.ready = False
        super().__init__(intents=intents)

    async def on_ready(self):
        """on_ready patch"""
        self.ready = True
        logger.success(f"{self.user} now up!")
        
class FatesWorkerOauth(Singleton):  # pylint: disable=too-few-public-methods
    """Stores all oauths (currently only discord)"""
    
    def __init__(
        self,
        *,
        discord_oauth: DiscordOauth
    ):
        self.discord = discord_oauth

class FatesWorkerSession(Singleton):  # pylint: disable=too-many-instance-attributes
    """Stores a worker session"""

    def __init__(
        self,
        *, 
        session_id: str,
        postgres: asyncpg.Pool,
        redis: aioredis.Connection,
        oauth: FatesWorkerOauth
    ):
        self.id = session_id
        self.postgres = postgres
        self.redis = redis
        self.oauth = oauth

        # Record basic stats and initially set workers to None
        self.start_time = time.time()
        self.up = False
        self.workers = None
        
        # FUP = finally up/all workers are now up
        self.fup = False
        
        # Used in shutdown to check if already dead
        self.dying = False
        
        # Templating
        self.templates = Jinja2Templates(directory="data/templates")

    def set_up(self):
        """Set the worker to up"""
        self.up = True

    def publish_workers(self, workers):
        """Publish workers"""
        self.workers = workers
        self.workers.sort()
        self.fup = True

    def primary_worker(self):
        """Returns if we are primary (first) worker"""
        return self.fup and self.workers[0] == os.getpid()

    def get_worker_index(self):
        """
        This function should only be called 
        after workers are published
        """
        return self.workers.index(os.getpid())

def setup_discord():
    """Sets up discord clients"""
    intent_main = discord.Intents(
        guilds=True,
        members=True,
        presences=True
    )
    intent_servers = discord.Intents(
        guilds = True
    )
    intent_dbg = discord.Intents(
        dm_messages = True  # Only allow DMs to pass through
    ) 
    client = FatesBot(intents=intent_main)
    client_server = FatesBot(intents=intent_servers)
    client_dbg = FatesDebugBot(intents=intent_dbg)
    logger.info("Discord init is beginning")
    asyncio.create_task(client.start(TOKEN_MAIN))
    asyncio.create_task(client_server.start(TOKEN_SERVER)) 
    return {"main": client, "servers": client_server, "debug": client_dbg}

# Include all the modules by looping through 
# and using importlib to import them and then including them in fastapi


async def init_fates_worker(app, session_id, workers):
    """
    On startup:
        - Initialize Postgres andRedis
        - Setup the ratelimiter and IPC worker protocols
        - Start repeated task for vote reminder posting
    """
    # This is still builtins for backward compatibility. 
    # ========================================================
    # Move all code to use worker session. All new code should 
    # always use worker session instead of builtins
    dbs = await setup_db()

    # Wait for redis ipc to come up
    app.state.ipc_up = False
    app.state.first_run = True

    @app.middleware("http")
    async def _maint(request, call_next):
        if request.app.state.ipc_up:
            return await call_next(request)
        return RedirectResponse("/maint/page")

    async def wait_for_ipc(app, session_id, workers, dbs):
        while True:
            if not app.state.ipc_up:
                logger.info("Waiting for IPC")
            else:
                logger.info("Doing periodic IPC health check")
            resp = await redis_ipc_new(dbs["redis"], "PING", timeout=5)
            logger.info(resp)
            if not resp:
                invalid = True
                reason = "IPC not up"
            else:
                resp1 = resp.decode("utf-8")
                invalid, reason = False, "All good!"
                respl = resp1.split(" ")
                if len(respl) != 3:
                    invalid, reason = True, "Invalid PONG payload"
                if respl[0] != "PONG":
                    invalid, reason = True, "IPC corrupt"
                if respl[1] != "V3":
                    invalid, reason = True, f"Invalid IPC version: {respl[1]}"

                if not invalid:
                    app.state.site_degraded = (respl[2] == "1")
        
            if invalid:
                app.state.ipc_up = False
                await asyncio.sleep(3)
                logger.info(f"Invalid IPC. Got invalid PONG: {resp} (reason: {reason})")
                app.state.ipc_up = False
                continue
            elif app.state.first_run:
                app.state.first_run = False
                await finish_init(app, session_id, workers, dbs)
            else:
                app.state.ipc_up = True
                await asyncio.sleep(30)
            await asyncio.sleep(60)
    
    asyncio.create_task(wait_for_ipc(app, session_id, workers, dbs))

async def finish_init(app, session_id, workers, dbs):
    builtins.db = dbs["postgres"]
    builtins.redis_db = dbs["redis"]
    logger.success("Connected to postgres and redis")

    app.state.worker_session = FatesWorkerSession(
        session_id=session_id,
        postgres=dbs["postgres"],
        redis=dbs["redis"],
        oauth=FatesWorkerOauth(
            discord_oauth=DiscordOauth(
                oc=OauthConfig(
                    client_id=discord_client_id,
                    client_secret=discord_client_secret,
                    redirect_uri=discord_redirect_uri,
                    lynxfall_key=lynxfall_key
                ),
            )
        )
    )

    # Create the shutdown handler to work around uvicorn faults
    loop = asyncio.get_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT, signal.SIGQUIT):
        loop.add_signal_handler(sig, shutdown_fates_worker(app))

    # Set the session for use in startup
    session = app.state.worker_session
    
    # Set bot tags
    def _tags(tag_db):
        tags = {}
        for tag in tag_db:
            tags = tags | {tag["id"]: tag["icon"]}
        return tags

    tags_db = await session.postgres.fetch(
        "SELECT id, icon FROM bot_list_tags"
    )
    tags = _tags(tags_db)
    builtins.TAGS = tags
    builtins.tags_fixed = calc_tags(tags)

    # Setup sessions (one day expiry)
    app.add_middleware(
        SessionMiddleware, 
        secret_key=session_key, 
        https_only=True,
        max_age=60 * 60 * 12, 
        same_site='strict'
    )  
    
    # Setup sentry
    sentry_sdk.init(sentry_dsn)  # pylint: disable=abstract-class-instantiated
    app.add_middleware(SentryAsgiMiddleware)

    # Setup ratelimiter
    LynxfallLimiter.init(session.redis, identifier=rl_key_func)

    # Setup trusted host middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[site, "127.0.0.1", "0.0.0.0"])

    # Add GZip handling
    app.add_middleware(GZipMiddleware, minimum_size=500)
    
    # Setup exception handling
    @app.exception_handler(403)
    @app.exception_handler(404)
    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    @app.exception_handler(500)
    @app.exception_handler(HTTPException)
    @app.exception_handler(Exception)
    @app.exception_handler(StarletteHTTPException)
    async def _fl_error_handler(request, exc):
        return await WebError.error_handler(request, exc, log=True)
    
    # Add request handler
    app.add_middleware(
        FatesListRequestHandler, 
        exc_handler=WebError.error_handler
    )
    
    # Include all routers
    include_routers(app, "Discord", "modules/discord")

    # Begin worker sync
    asyncio.create_task(catclient(workers, session, app))
    logger.debug("Started catclient task")

    # We are now up (probably)
    app.state.worker_session.set_up()

    # Boast about oht success!
    logger.success(
        f"Fates List worker (pid: {os.getpid()}) bootstrapped successfully!"
    )
 
    # We are ready to handle requests
    app.state.ipc_up = True

        
async def catclient(workers, session, app):
    """The Fates List Dragon IPC protocol"""
    await session.redis.publish(
        "_worker_fates", 
        f"UP {session.id} {os.getpid()} {workers}"
    )

    pubsub = session.redis.pubsub()
    
    await pubsub.subscribe("_worker_fates")
    async for msg in pubsub.listen():
        if not msg or not isinstance(msg.get("data"), bytes):
            continue
        msg = tuple(msg.get("data").decode("utf-8").split(" "))
        logger.trace(f"Got {msg}")
        match msg:
            case ("RESTART", tgt):
                if tgt == "*" or (tgt.isdigit() and int(tgt) == os.getpid()):
                    logger.info(f"Dying due to sent RESTART call with requestor being {tgt}")
                    signal.raise_signal(signal.SIGINT)
                    os._exit(0)

            # IPC going up has no session id yet
            case("REGET", reason):
                # Announce that we are up and sending to repeat a message
                logger.info("Sending IPC info due to reget")
                await session.redis.publish(
                    "_worker_fates", 
                    f"UP {session.id} {os.getpid()} {workers}"
                )

            # FUP = finally up
            case("FUP", session_id, *worker_lst):
                if session_id != session.id:  # noqa: F821
                    continue
                logger.success("All workers are up!")

                # Finally up!
                try:
                    session.publish_workers(
                        [int(worker) for worker in worker_lst]  # noqa: F821
                    )

                except ValueError:
                    logger.warning(
                        f"Got invalid workers from ipc ({workers})"
                    )
               
                #await start_dbg(session, app)
                #asyncio.create_task(vote_reminder(session))

            case _:
                pass  # Ignore the rest for now


async def vote_reminder(session):
    """Vote reminders task"""
    if session.primary_worker():
        events = importlib.import_module("modules.core.events")
        bot_add_event = events.bot_add_event
        reminders = await session.postgres.fetch(
            """SELECT user_id, bot_id FROM user_reminders 
            WHERE remind_time >= NOW() AND resolved = false"""
        )
    
        for reminder in reminders:
            logger.debug(f"Got reminder {reminder}")
            await bot_add_event(
                reminder["bot_id"], 
                enums.APIEvents.vote_reminder, 
                {"user": str(reminder["user_id"])}
            )

            await session.postgres.execute(
                """UPDATE user_reminders SET resolved = true 
                WHERE user_id = $1 AND bot_id = $2""", 
                reminder["user_id"], 
                reminder["bot_id"]
            )
    
        await asyncio.sleep(60 * 15)
        await vote_reminder(session)


def calc_tags(list_tags):
    """Calculate bot list tags"""
    # Tag calculation
    tags_fixed = []
    for tag in list_tags.keys():
        # For every key in tag dict, 
        # create the "fixed" tag information 
        # (friendly and easy to use data for tags)
        tags_fixed.append({
            "name": tag.replace("_", " ").title(),
            "iconify_data": list_tags[tag], 
            "id": tag
        })
    return tags_fixed


async def setup_db():
    """Function to setup the asyncpg connection pool"""
    postgres = await asyncpg.create_pool()
    redis = await aioredis.from_url('redis://localhost:1001', db=1)
    return {"postgres": postgres, "redis": redis}


def shutdown_fates_worker(app):
    """Shutdown the list properly"""
    worker_session = app.state.worker_session
    db = worker_session.postgres
    redis = worker_session.redis

    async def _close():
        await asyncio.sleep(0)
        await db.close()
        await redis.publish("_worker", f"DOWN WORKER {os.getpid()}")
        await redis.close()
        await asyncio.sleep(0)

    def _signal_handler_entry():
        """Entrypoint for signal handler"""

        # Ensure only one stop task is executed
        if worker_session.dying:
            return

        # We are going to die
        worker_session.dying = True

        # Begin killing fates list
        logger.info("Killing Fates List")
        task = asyncio.create_task(_close())
        task.add_done_callback(_gohome)

    def _gohome(_):
        logger.info("Fates List is now down. Going back to the IceWings!")
        os._exit(0)

    return _signal_handler_entry
