from .imports import *
from .ratelimits import *
from .rabbitmq import *
from discord import Client
from discord.ext import commands
    
class FatesDebugBot(commands.Bot):
    def __init__(self, *, intents):
        self.ready = False
        super().__init__(command_prefix=commands.when_mentioned_or('fl!'), intents = intents)

    async def is_owner(self, user: discord.User):
        if user.id == owner:
            return True
        return False

    async def on_ready(self):
        self.ready = True
        logger.info(f"{self.user} (DEBUG BOT) should now be up on first worker")

class FatesWorkerSessionDiscord():
    """Stores discord clients for a worker session"""
    def __init__(self, *, main, servers):
        self.dbg = None
        self.main = main
        self.servers = servers

    def up(self):
        """Returns whether the main client is up"""
        return self.main.user is not None

class FatesWorkerSession():
    """Stores a worker session"""
    def __init__(self, *, id, db, redis, rabbit, discord):
        self.id = id
        self.db = db
        self.start_time = time.time()
        self.redis = redis
        self.rabbit = rabbit
        self.up = False
        self.workers = None
        self.fup = False # FUP = finally up/all workers are now up
        self.discord = discord

    def up(self):
        self.up = True

    def publish_workers(self, workers):
        self.workers = workers
        self.fup = True

    def primary_worker(self):
        return self.fup and self.workers[0] == os.getpid()

class FatesBot(Client):
    def __init__(self, *, intents):
        self.ready = False
        super().__init__(intents = intents)

    async def on_ready(self):
        self.ready = True
        logger.info(f"{self.user} now up!")

def setup_discord():
    intent_main = discord.Intents.none()
    intent_main.guilds = True
    intent_main.members = True
    intent_main.presences = True
    intent_servers = discord.Intents.none()
    intent_servers.guilds = True
    intent_servers.members = True
    intent_dbg = discord.Intents.none()
    intent_dbg.guilds = True
    intent_dbg.dm_messages = True # We only want DM messages, not guild
    client = FatesBot(intents=intent_main)
    client_server = FatesBot(intents=intent_servers)
    client_dbg = FatesDebugBot(intents=intent_dbg)
    return client, client_server, client_dbg

# Include all the modules by looping through and using importlib to import them and then including them in fastapi
def include_routers(app, fname, rootpath):
    for root, dirs, files in os.walk(rootpath):
        if not root.startswith("_") and not root.startswith(".") and not root.startswith("debug"):
            rrep = root.replace("/", ".")
            for f in files:
                if not f.startswith("_") and not f.startswith(".") and not f.endswith("pyc") and not f.startswith("models") and not f.startswith("base"):
                    path = f"{rrep}.{f.replace('.py', '')}"
                    logger.debug(f"{fname}: {root}: Loading {f} with path {path}")
                    route = importlib.import_module(path)
                    app.include_router(route.router)
                         
async def startup_tasks(app):
    """
    On startup:
        - Initialize the database
        - Get bot and server tags
        - Start the main and server bots using tokens in config_secrets.py
        - Sleep for 4 seconds to ensure connections are made before application startup
        - Setup Redis and initialize the ratelimiter and caching system
        - Connect robustly to rabbitmq for add bot/edit bot/delete bot
        - Start repeated task for vote reminder posting
        - Listen for broadcast events
    """
    # TODO: This is still builtins for backward compatibility. Move all code to use worker session and new code should always use this
    dbs = await setup_db()
    builtins.db = dbs["postgres"]
    builtins.redis_db = dbs["redis"]
    builtins.rabbitmq_db = dbs["rabbit"]
    logger.success("Connected to postgres, rabbitmq and redis")
    
    app.state.worker_session = FatesWorkerSession(
        id = os.environ.get("SESSION_ID"),
        db = db, 
        redis = redis_db, 
        rabbit = rabbitmq_db,
        discord = FatesWorkerSessionDiscord(
            main = client,
            servers = client_servers
        )
    )

    # Set bot tags
    def _tags(tag_db):
        tags =  {}
        for tag in tags_db:
            tags = tags | {tag["id"]: tag["icon"]}
        return tags
    
    tags_db = await db.fetch("SELECT id, icon FROM bot_list_tags")    
    tags = _tags(tags_db)
    builtins.TAGS = tags
    builtins.tags_fixed = calc_tags(tags)
    logger.info("Discord init beginning")
    asyncio.create_task(client.start(TOKEN_MAIN))
    asyncio.create_task(client_servers.start(TOKEN_SERVER))
    workers = os.environ.get("WORKERS")
    app.add_middleware(SessionMiddleware, secret_key=session_key, https_only = True, max_age = 60*60*12, same_site = 'strict') # 1 day expiry cookie
    LynxfallLimiter.init(redis_db, identifier = rl_key_func)

    # Announce that we are up and not a repeat
    asyncio.create_task(status(workers, app.state.worker_session))

    logger.debug("Started status task")

    app.state.worker_session.up = True
    asyncio.create_task(vote_reminder())

async def start_dbg(session):
    if session.primary_worker():
        client_dbg.bots_role = bots_role
        client_dbg.bot_dev_role = bot_dev_role
        client_dbg.load_extension("jishaku")
        manager = importlib.import_module("modules.debug.bot")
        client_dbg.add_cog(manager.Manager(client_dbg))
        asyncio.create_task(client_dbg.start(TOKEN_MAIN))
        return
        
async def status(workers, session):
    await redis_db.publish(f"{instance_name}._worker", f"{session.id} UP WORKER {os.getpid()} 0 {workers}")
    pubsub = redis_db.pubsub()
    
    await pubsub.subscribe(f"{instance_name}._worker")
    async for msg in pubsub.listen():
        if msg is None or type(msg.get("data")) != bytes:
            continue
        msg = tuple(msg.get("data").decode("utf-8").split(" "))
        logger.debug(f"Got {msg}") 
        match msg:
            # RabbitMQ going up has no session id yet
            case ("NOSESSION", "UP", "RMQ", _):
                # Announce that we are up and sending to repeat a message
                logger.info("Sending RMQ info due to new worker")
                await redis_db.publish(f"{instance_name}._worker", f"{session.id} UP WORKER {os.getpid()} 1 {workers}") 
   
            case (session_id, "REGET", "WORKER", reason):
                if session_id != session.id:
                    # Ignore this
                    continue

                logger.warning(f"RabbitMQ requesting REGET with reason {reason}")
                # Announce that we are up and sending to repeat a message
                await redis_db.publish(f"{instance_name}._worker", f"{session.id} UP WORKER {os.getpid()} 1 {workers}") 
            
            # FUP = finally up
            case (session_id, "FUP", *worker_lst):
                logger.success("All workers are up!")
                if session_id != session.id:
                    continue

                # Finally up!
                try:
                    session.publish_workers([int(worker) for worker in worker_lst])
                
                except ValueError:
                    logger.warning(f"Got invalid workers from rabbitmq ({workers})")

                await start_dbg(session)

            case _:
                pass # Ignore the rest for now

@repeat_every(seconds=60)
async def vote_reminder():
    reminders = await db.fetch("SELECT user_id, bot_id FROM user_reminders WHERE remind_time >= NOW() WHERE resolved = false")
    for reminder in reminders:
        logger.debug(f"Got reminder {reminder}")
        await bot_add_event(reminder["bot_id"], enums.APIEvents.vote_reminder, {"user": str(reminder["user_id"])})
        await db.execute("UPDATE user_reminders SET resolved = true WHERE user_id = $1 AND bot_id = $2", reminder["user_id"], reminder["bot_id"])
 
def calc_tags(TAGS):
    # Tag calculation
    tags_fixed = []
    for tag in TAGS.keys():
        # For every key in tag dict, create the "fixed" tag information (friendly and easy to use data for tags)
        tags_fixed.append({"name": tag.replace("_", " ").title(), "iconify_data": TAGS[tag], "id": tag})
    return tags_fixed

async def setup_db():
    """Function to setup the asyncpg connection pool"""
    postgres = await asyncpg.create_pool(host="localhost", port=12345, user=pg_user, database=f"fateslist_{instance_name}", password = pg_pwd)
    redis = await aioredis.from_url('redis://localhost:12348', db = 1)
    rabbit = await aio_pika.connect_robust(
        f"amqp://meow:{rabbitmq_pwd}@127.0.0.1/"
    )
    return {"postgres": postgres, "redis": redis, "rabbit": rabbit}

def fl_openapi(app):
    def _openapi():
        """Custom OpenAPI description"""
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title="Fates List",
            version="1.0",
            description="Only v2 beta 3 API is supported (v1 is the old one that fateslist.js currently uses). The default API is v2. This means /api will point to this. To pin a api, either use the FL-API-Version header or directly use /api/v{version}.",
            routes=app.routes,
        )
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    return _openapi
