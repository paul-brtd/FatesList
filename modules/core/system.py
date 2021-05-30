from .imports import *

def setup_discord():
    intent_main = discord.Intents.default()
    intent_main.typing = False
    intent_main.bans = False
    intent_main.emojis = False
    intent_main.integrations = False
    intent_main.webhooks = False
    intent_main.invites = False
    intent_main.voice_states = False
    intent_main.messages = False
    intent_main.members = True
    intent_main.presences = True
    client = discord.Client(intents=intent_main)
    intent_server = deepcopy(intent_main)
    intent_server.presences = False
    client_server = discord.Client(intents=intent_server)
    return client, client_server

# Include all the modules by looping through and using importlib to import them and then including them in fastapi
def include_routers(app, fname, rootpath):
    for root, dirs, files in os.walk(rootpath):
        if not root.startswith("_") and not root.startswith("."):
            rrep = root.replace("/", ".")
            for f in files:
                if not f.startswith("_") and not f.startswith(".") and not f.endswith("pyc"):
                    path = f"{rrep}.{f.replace('.py', '')}"
                    logger.debug(f"{fname}: {root}: Loading {f} with path {path}")
                    route = importlib.import_module(path)
                    app.include_router(route.router)

                         
async def startup_tasks():
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
    builtins.up = False
    builtins.db = await setup_db()

    # Set bot tags
    def _tags(tag_db):
        tags =  {}
        for tag in tags_db:
            tags = tags | {tag["id"]: tag["icon"]}
        return tags
    
    tags_db = await db.fetch("SELECT id, icon FROM bot_list_tags WHERE type = 0 or type = 2")    
    tags_db_server = await db.fetch("SELECT id, icon FROM bot_list_tags WHERE type = 1 or type = 2")
    tags = _tags(tags_db)
    tags_server = _tags(tags_db_server)
    builtins.TAGS = tags
    builtins.TAGS_SERVER = tags_server
    builtins.tags_fixed = calc_tags(tags)
    builtins.tags_fixed = calc_tags(tags_server) 
    logger.info("Discord init beginning")
    asyncio.create_task(client.start(TOKEN_MAIN))
    asyncio.create_task(client_servers.start(TOKEN_SERVER))
    builtins.redis_db = await aioredis.from_url('redis://localhost', db = 1)
    workers = os.environ.get("WORKERS")
    asyncio.create_task(status(workers))
    await asyncio.sleep(4)
    app.add_middleware(SessionMiddleware, secret_key=session_key, https_only = True, max_age = 60*60*12) # 1 day expiry cookie
    FastAPILimiter.init(redis_db, identifier = rl_key_func)
    builtins.rabbitmq_db = await aio_pika.connect_robust(
        f"amqp://fateslist:{rabbitmq_pwd}@127.0.0.1/"
    )
    builtins.up = True
    await redis_db.publish("_worker", f"UP WORKER {os.getpid()} 0 {workers}") # Announce that we are up and not a repeat
    await vote_reminder()

async def status(workers):
    pubsub = redis_db.pubsub()
    await pubsub.subscribe("_worker")
    async for msg in pubsub.listen():
        if msg is None or type(msg.get("data")) != bytes:
            continue
        msg = msg.get("data").decode("utf-8").split(" ")
        match msg:
            case ["UP", "RMQ", _]:
                await redis_db.publish("_worker", f"UP WORKER {os.getpid()} 1 {workers}") # Announce that we are up and sending to repeat a message
            case ["REGET", "WORKER", reason]:
                logger.warning(f"RabbitMQ requesting REGET with reason {reason}")
                await redis_db.publish("_worker", f"UP WORKER {os.getpid()} 1 {workers}") # Announce that we are up and sending to repeat a message
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
