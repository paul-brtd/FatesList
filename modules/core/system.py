"""Fates List System Bootstrapper"""
from .ratelimits import rl_key_func

from config import (
    TOKEN_MAIN, TOKEN_SERVER, bots_role, 
    bot_dev_role, worker_key, session_key, 
    owner, sentry_dsn, lynxfall_key,
    discord_client_id, discord_client_secret,
    discord_redirect_uri, site, TOKEN_DBG,
    API_VERSION
)

import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.openapi.utils import get_openapi
import discord
from discord.ext import commands
from lynxfall.core.classes import Singleton
from lynxfall.utils.fastapi import include_routers, api_versioner  
from lynxfall.ratelimits import LynxfallLimiter
from lynxfall.rabbit.client import RabbitClient
from lynxfall.oauth.models import OauthConfig
from lynxfall.oauth.providers.discord import DiscordOauth
import asyncpg
import os
import time
import datetime
from loguru import logger
import aioredis
import aio_pika
import asyncio
import importlib
import uuid
from http import HTTPStatus
import builtins
from modules.models import enums
import signal
import sys
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import start_http_server
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import (
    HTTPException,
    ValidationError,
    RequestValidationError
)
from modules.core.error import WebError


class FatesListRequestHandler(BaseHTTPMiddleware):
    """Request Handler for Fates List"""
    def __init__(self, app, *, exc_handler):
        super().__init__(app)
        self.exc_handler = exc_handler
        
        # Methods that should be allowed by CORS
        self.CORS_ALLOWED = "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS"
    
        # Default response
        self.default_res = HTMLResponse(
            "Something happened!", 
            status_code=500
        ) 
        
    def logger(self, path, request, response):
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

        try:
            res = await self._dispatcher(path, request, call_next)
        except Exception as exc:
            logger.exception("Site Error Occurred") 
            res = await self.exc_handler(request, exc, log=True)
        
        self.logger(path, request, res)
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
        except Exception as exc:
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
        
        response.headers[acam] = self.CORS_ALLOWED
        if response.status_code == 405:
            if request.method == "OPTIONS" and is_api:
                response.status_code = 204
                response.headers["Allow"] = self.CORS_ALLOWED
        
        return response


class FatesDebugBot(commands.Bot):
    """Fates List Debug Bot"""
    def __init__(self, *, intents):
        self.ready = False
        super().__init__(
            command_prefix=commands.when_mentioned_or('fl!'), intents=intents)

    async def is_owner(self, user: discord.User):
        if user.id == owner:
            return True
        return False

    async def on_ready(self):
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
        self.ready = True
        logger.success(f"{self.user} now up!")        

        
class FatesWorkerOauth(Singleton):
    """Stores all oauths (currently only discord)"""
    
    def __init__(
        self,
        *,
        discord: DiscordOauth
    ):
        self.discord = discord

        
class FatesWorkerDiscord(Singleton):
    """Stores discord clients for a worker session"""

    def __init__(
        self, 
        *, 
        main: FatesBot, 
        servers: FatesBot, 
        debug: FatesDebugBot
    ):
        self.debug = debug
        self.main = main
        self.servers = servers

    def up(self):
        """Returns whether the main client is up"""
        return self.main.user is not None


class FatesWorkerSession(Singleton):
    """Stores a worker session"""

    def __init__(
        self,
        *, 
        id: str,
        postgres: asyncpg.Pool,
        redis: aioredis.Connection,
        rabbit: aio_pika.RobustConnection,
        discord: FatesWorkerDiscord, 
        oauth: FatesWorkerOauth
    ):
        self.id = id
        self.postgres = postgres
        self.redis = redis
        self.rabbit = rabbit
        self.discord = discord
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

    def is_up(self):
        self.up = True

    def publish_workers(self, workers):
        self.workers = workers
        self.fup = True

    def primary_worker(self):
        return self.fup and self.workers[0] == os.getpid()

    def get_worker_index(self):
        """
        This function should only be called 
        after workers are published
        """
        return self.workers.index(os.getpid())


async def setup_discord():
    intent_main = discord.Intents.none()
    intent_main.guilds = True
    intent_main.members = True
    intent_main.presences = True
    intent_servers = discord.Intents.none()
    intent_servers.guilds = True
    intent_servers.members = False
    intent_dbg = discord.Intents.none()
    intent_dbg.guilds = True
    intent_dbg.dm_messages = True  # We only want DM messages, not guild
    client = FatesBot(intents=intent_main)
    client_server = FatesBot(intents=intent_servers)
    client_dbg = FatesDebugBot(intents=intent_dbg)
    logger.info("Discord init beginning")
    asyncio.create_task(client.start(TOKEN_MAIN))
    asyncio.create_task(client_server.start(TOKEN_SERVER))
    return {"main": client, "servers": client_server, "debug": client_dbg}

# Include all the modules by looping through 
# and using importlib to import them and then including them in fastapi


async def init_fates_worker(app):
    """
    On startup:
        - Initialize Postgres, Redis, RabbitMQ and discord
        - Setup the ratelimiter and RabbitMQ worker protocols
        - Start repeated task for vote reminder posting
    """
    # TODO: This is still builtins for backward compatibility. 
    # ========================================================
    # Move all code to use worker session. All new code should 
    # always use worker session instead of builtins
    metric_p = Instrumentator()
    metric_p.instrument(app)

    dbs = await setup_db()
    discord = await setup_discord()
    builtins.db = dbs["postgres"]
    builtins.redis_db = dbs["redis"]
    builtins.rabbitmq_db = dbs["rabbit"]
    builtins.client = builtins.dclient = discord["main"]
    builtins.client_server = discord["servers"]
    RabbitClient.setup(worker_key, dbs["redis"], dbs["rabbit"])
    logger.success("Connected to postgres, rabbitmq and redis")

    app.state.worker_session = FatesWorkerSession(
        id=os.environ.get("SESSION_ID"),
        postgres=dbs["postgres"],
        redis=dbs["redis"],
        rabbit=dbs["rabbit"],
        discord=FatesWorkerDiscord(
            main=discord["main"],
            servers=discord["servers"],
            debug=discord["debug"]
        ),
        oauth=FatesWorkerOauth(
            discord=DiscordOauth(
                oc=OauthConfig(
                    client_id=discord_client_id,
                    client_secret=discord_client_secret,
                    redirect_uri=discord_redirect_uri,
                    lynxfall_key=lynxfall_key
                ),
                redis=dbs["redis"]
            )
        )
    )

    # Create the shutdown handler to work around uvicorn faults
    loop = asyncio.get_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGABRT, signal.SIGQUIT):
        loop.add_signal_handler(sig, shutdown_fates_list(app))

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
    sentry_sdk.init(sentry_dsn)
    app.add_middleware(SentryAsgiMiddleware)

    # Setup ratelimiter
    LynxfallLimiter.init(session.redis, identifier=rl_key_func)

    # Setup trusted host middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[site])

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

    # Setup oenapi
    app.openapi = fl_openapi(app)

    # Get number of workers for worker syncing
    workers = os.environ.get("WORKERS")

    # Begin worker sync
    asyncio.create_task(status(workers, session, app))
    logger.debug("Started status task")

    # We are now up (probably)
    app.state.worker_session.is_up()

    # Boast about oht success!
    logger.success(
        f"Fates List worker (pid: {os.getpid()}) bootstrapped successfully!"
    )
   

async def start_dbg(session, app):
    if session.primary_worker():
        session.discord.debug.bots_role = bots_role
        session.discord.debug.bot_dev_role = bot_dev_role
        
        try:
            session.discord.debug.load_extension("jishaku")
        except Exception:
            pass
        
        manager = importlib.import_module("modules.debug.bot")
        session.discord.debug.add_cog(manager.Manager(session.discord.debug, app))
        asyncio.create_task(session.discord.debug.start(TOKEN_DBG))


async def status(workers, session, app):
    await session.redis.publish(
        "_worker", 
        f"{session.id} UP WORKER {os.getpid()} 0 {workers}"
    )

    pubsub = session.redis.pubsub()

    await pubsub.subscribe("_worker")
    async for msg in pubsub.listen():
        if not msg or not isinstance(msg.get("data"), bytes):
            continue
        msg = tuple(msg.get("data").decode("utf-8").split(" "))
        logger.debug(f"Got {msg}")
        match msg:
            # RabbitMQ going up has no session id yet
            case("NOSESSION", "UP", "RMQ", _):
                # Announce that we are up and sending to repeat a message
                logger.info("Sending RMQ info due to new worker")
                await session.redis.publish(
                    "_worker", 
                    f"{session.id} UP WORKER {os.getpid()} 1 {workers}"
                )

            case(session_id, "REGET", "WORKER", reason):
                if session_id != session.id:  # noqa: F821
                    continue

                logger.warning(
                    f"RabbitMQ REGET: {reason}"  # noqa: F821
                ) 
                # Announce that we are up and sending to repeat a message
                await session.redis.publish(
                    "_worker", 
                    f"{session.id} UP WORKER {os.getpid()} 1 {workers}"
                )

            # FUP = finally up
            case(session_id, "FUP", *worker_lst):
                logger.success("All workers are up!")
                if session_id != session.id:  # noqa: F821
                    continue

                # Finally up!
                try:
                    session.publish_workers(
                        [int(worker) for worker in worker_lst]  # noqa: F821
                    )

                except ValueError:
                    logger.warning(
                        f"Got invalid workers from rabbitmq ({workers})"
                    )
                
                start_http_server(3000 + session.get_worker_index())

                await start_dbg(session, app)
                asyncio.create_task(vote_reminder(session))

            case _:
                pass  # Ignore the rest for now


async def vote_reminder(session):
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
        return await vote_reminder(session)


def calc_tags(TAGS):
    # Tag calculation
    tags_fixed = []
    for tag in TAGS.keys():
        # For every key in tag dict, 
        # create the "fixed" tag information 
        # (friendly and easy to use data for tags)
        tags_fixed.append({"name": tag.replace("_", " ").title(),
                          "iconify_data": TAGS[tag], "id": tag})
    return tags_fixed


async def setup_db():
    """Function to setup the asyncpg connection pool"""
    postgres = await asyncpg.create_pool()
    redis = await aioredis.from_url('redis://localhost:1001', db=1)
    rabbit = await aio_pika.connect_robust(host="localhost", port=1002)
    return {"postgres": postgres, "redis": redis, "rabbit": rabbit}


def fl_openapi(app):
    def _openapi():
        """Custom OpenAPI description"""
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title="Fates List",
            version="1.0",
            description="""
            Current API: v2 beta 3
            Default API: v2
            API Docs: https://apidocs.fateslist.xyz
            """,
            routes=app.routes,
        )
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    return _openapi


def shutdown_fates_list(app):
    worker_session = app.state.worker_session
    db = worker_session.postgres
    rabbit = worker_session.rabbit
    redis = worker_session.redis

    async def _close():
        logger.info("Closing connections")
        await asyncio.sleep(0)
        await db.close()
        await rabbit.close()
        await redis.publish("_worker", f"DOWN WORKER {os.getpid()}")
        await redis.close()
        await asyncio.sleep(0)
        logger.info("All connections closed")

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

    def _gohome(task):
        logger.info("Fates List is now down. Going back to the IceWings!")
        sys.exit(0)

    return _signal_handler_entry
