"""Fates List System Init/Maintenance"""
from .ratelimits import rl_key_func
from .events import bot_add_event

from config import (
    TOKEN_MAIN, TOKEN_SERVER, bots_role, 
    bot_dev_role, worker_key, session_key, 
    owner, sentry_dsn
)

import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from starlette.middleware.sessions import SessionMiddleware
from fastapi.openapi.utils import get_openapi
import discord
from discord.ext import commands
from lynxfall.core.classes import Singleton
from lynxfall.ratelimits import LynxfallLimiter
from lynxfall.rabbit.client import RabbitClient
from lynxfall.oauth.models import OauthConfig
from lynxfall.oauth.providers.discord import DiscordOauth
import asyncpg
import os
import time
from loguru import logger
import aioredis
import aio_pika
import asyncio
import importlib
import builtins
import modules.models.enums as enums


class FatesDebugBot(commands.Bot):
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
        logger.info(
            f"{self.user} (DEBUG BOT) should now be up on first worker")

        
class FatesBot(discord.Client):
    def __init__(self, *, intents):
        self.ready = False
        super().__init__(intents=intents)

    async def on_ready(self):
        self.ready = True
        logger.info(f"{self.user} now up!")        

        
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

    def __init__(self, *, main: FatesBot, servers: FatesBot, debug: FatesDebug):
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
        redis: aioredis,Connection,
        rabbit: aio_pika.RobustConnection,
        discord: FatesWorkerDiscord, 
        oauth: FatesWorkerOauth
    ):
        self.id = id
        self.postgres = postgres
        self.start_time = time.time()
        self.redis = redis
        self.rabbit = rabbit
        self.up = False
        self.workers = None
        self.fup = False  # FUP = finally up/all workers are now up
        self.discord = discord
        self.oauth = oauth

    def up(self):
        self.up = True

    def publish_workers(self, workers):
        self.workers = workers
        self.fup = True

    def primary_worker(self):
        return self.fup and self.workers[0] == os.getpid()


async def setup_discord():
    intent_main = discord.Intents.none()
    intent_main.guilds = True
    intent_main.members = True
    intent_main.presences = True
    intent_servers = discord.Intents.none()
    intent_servers.guilds = True
    intent_servers.members = True
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


def include_routers(app, fname, rootpath):
    logger.info(f"Loading modules for Fates List: {fname}")
    for root, dirs, files in os.walk(rootpath):
        if (not root.startswith("_") 
            and not root.startswith(".") 
            and not root.startswith("debug")
        ):

            rrep = root.replace("/", ".")
            for f in files:
                if (not f.startswith("_") 
                    and not f.startswith(".") 
                    and not f.endswith("pyc") 
                    and not f.startswith("models") 
                    and not f.startswith("base")
                ):
                    path = f"{rrep}.{f.replace('.py', '')}"
                    logger.debug(
                        f"{fname}: {root}: Loading {f} with path {path}")
                    route = importlib.import_module(path)
                    app.include_router(route.router)

    logger.info(f"Done init of {fname}")


async def init_fates_worker(app):
    """
    On startup:
        - Initialize Postgres, Redis, RabbitMQ and discord
        - Setup the ratelimiter and RabbitMQ worker protocols
        - Start repeated task for vote reminder posting
    """
    # TODO: This is still builtins for backward compatibility. 
    # =======================================================
    # Move all code to use worker session and new code should 
    # always use worker session
    dbs = await setup_db()
    discord = await setup_discord()
    builtins.db = dbs["postgres"]
    builtins.redis_db = dbs["redis"]
    builtins.rabbitmq_db = dbs["rabbit"]
    builtins.client = discord["main"]
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
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri=redirect_uri,
                    lynxfall_key=jwt_auth_key
                ),
                redis=dbs["redis"]
            )
        )
    )

    session = app.state.worker_session

    # Set bot tags
    def _tags(tag_db):
        tags = {}
        for tag in tags_db:
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

    LynxfallLimiter.init(session.redis, identifier=rl_key_func)

    # Include all routers
    include_routers(app, "Discord", "modules/discord")

    # Setup oenapi
    app.openapi = fl_openapi(app)

    # Get number of workers for worker syncing
    workers = os.environ.get("WORKERS")

    # Begin worker sync
    asyncio.create_task(status(workers, session))
    logger.debug("Started status task")

    # We are now up (probably)
    app.state.worker_session.up = True


async def start_dbg(session):
    if session.primary_worker():
        session.discord.debug.bots_role = bots_role
        session.discord.debug.bot_dev_role = bot_dev_role
        session.discord.debug.load_extension("jishaku")
        manager = importlib.import_module("modules.debug.bot")
        session.discord.debug.add_cog(manager.Manager(session.discord.debug))
        asyncio.create_task(session.discord.debug.start(TOKEN_MAIN))
        return


async def status(workers, session):
    await session.redis.publish(
        "_worker", 
        f"{session.id} UP WORKER {os.getpid()} 0 {workers}"
    )

    pubsub = session.redis.pubsub()

    await pubsub.subscribe("_worker")
    async for msg in pubsub.listen():
        if msg is None or type(msg.get("data")) != bytes:
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

                await start_dbg(session)
                asyncio.create_task(vote_reminder(session))

            case _:
                pass  # Ignore the rest for now


async def vote_reminder(session):
    if session.primary_worker():
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
