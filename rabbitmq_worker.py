"""RabbitMQ worker"""
import asyncpg, asyncio, uvloop, aioredis, os, importlib
import nest_asyncio
nest_asyncio.apply()
import sys
sys.path.append("..")
from config import *
from aio_pika import *
import discord
import orjson
import builtins
from copy import deepcopy
from termcolor import colored, cprint
from modules.utils import secure_strcmp
from modules.core import *

# Import all needed backends
from rabbitmq.backends.bot_add import bot_add_backend
from rabbitmq.backends.bot_edit import bot_edit_backend
from rabbitmq.backends.bot_delete import bot_delete_backend
from rabbitmq.backends.server_add import server_add_backend
from rabbitmq.backends.events_webhook import events_webhook_backend

# Setup main bot

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
builtins.client = discord.Client(intents=intent_main)

# Server bot

intent_server = deepcopy(intent_main)
intent_server.presences = False

builtins.client_server = discord.Client(intents=intent_server)

async def dbg_test():
    return "HELLO"

def handle_await(code):
    if "await " not in code:
        return code.replace("return ", "ret = ")
    code = "".join(["    " + txt.lstrip() + "\n" for txt in code.lstrip().split('\n')])
    return f"""
async def task_runner():
{code}

ret = asyncio.run(task_runner())
"""

async def new_task(queue_name, friendly_name):
    _channel = await rabbitmq_db.channel()
    _queue = await _channel.declare_queue(queue_name, durable = True) # Function to handle our queue
    
    def serialized(obj):
        try:
            orjson.dumps({"rc": obj})
            return True
        except:
            return False

    async def _task(message: IncomingMessage):
        """RabbitMQ Queue Function"""
        print(f"{friendly_name} called")
        _json = orjson.loads(message.body)
        _headers = message.headers
        if not _headers:
            cprint(f"Invalid auth for {friendly_name}", "red")
            message.ack()
            return # No vlie auth sent
        if not secure_strcmp(_headers.get("auth"), worker_key):
            cprint(f"Invalid auth for {friendly_name} and JSON of {_json}", "red")
            message.ack()
            return # No valid auth sent

        if queue_name == "_admin" and _json["meta"].get("op"):
            # Handle admin operations
            rc = []
            err = []
            ops = _json["meta"]["op"]
            if type(ops) == str:
                ops = [ops]
            for op in ops:
                try:
                    op = handle_await(op)
                    loc = {}
                    exec(op.lstrip(), globals() | locals(), loc)
                    _ret = loc["ret"] if loc.get("ret") is not None else loc # Get return stuff
                    if not loc:
                        _ret = None # No return or anything
                    err.append(False)
                except Exception as exc:
                    cprint(exc, "red")
                    _ret = f"{type(exc).__name__}: {exc}"
                    err.append(True)
                rc.append(_ret if serialized(_ret) else str(_ret))

        else:
            # Normally handle rabbitmq task
            _task_handler = TaskHandler(_json, queue_name)
            rc = await _task_handler.handle()
            rc = rc if serialized(rc) else str(rc)
            err = False # Initially until we find exception

        _ret = {"ret": rc, "err": err} # Result to return
        if rc and isinstance(rc, Exception):
            cprint(rc, "red")
            _ret["ret"] = f"{type(rc).__name__}: {rc}"
            _ret["err"] = True # Mark the error
            stats.err_msgs.append(message) # Mark the failed message so we can ack it later

        if _json["meta"].get("ret"):
            await redis_db.set(f"rabbit-{_json['meta'].get('ret')}", orjson.dumps(_ret)) # Save return code in redis

        if queue_name == "_admin" or not _ret["err"]: # If no errors recorded
            message.ack()
        
    await _queue.consume(_task)

class Stats():
    def __init__(self):
        self.errors = 0 # Amount of errors
        self.exc = [] # Exceptions
        self.err_msgs = [] # All messages that failed

    def __str__(self):
        s = []
        for k in self.__dict__.keys():
            s.append(f"{k}: {self.__dict__[k]}")
        return "\n".join(s)

async def main():
    """Main worker function"""
    asyncio.create_task(client.start(TOKEN_MAIN))
    asyncio.create_task(client_server.start(TOKEN_SERVER))
    builtins.rabbitmq_db = await connect_robust(
        f"amqp://fateslist:{rabbitmq_pwd}@127.0.0.1/"
    )
    builtins.db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    builtins.redis_db = await aioredis.from_url('redis://localhost', db = 1)
    builtins.stats = Stats()
    channel = None
    while True: # Wait for discord.py before running tasks
        if channel is None:
            await asyncio.sleep(1)
            channel = client.get_channel(bot_logs)
        else:
            break
    await new_task("bot_edit_queue", "Edit Bot")
    await new_task("bot_add_queue", "Add Bot")
    await new_task("bot_delete_queue", "Delete Bot")
    await new_task("server_add_queue", "Add Server")
    await new_task("events_webhook_queue", "Event Webhook")
    await new_task("_admin", "Admin Command") # Special queue for admin commands sent
    print("Ready!")

class TaskHandler():
    handlers = {
        "bot_edit_queue": bot_edit_backend, 
        "bot_add_queue": bot_add_backend, 
        "bot_delete_queue": bot_delete_backend, 
        "events_webhook_queue": events_webhook_backend,
        "server_add_queue": server_add_backend
    }
    
    def __init__(self, dict, queue):
        self.ctx = dict["ctx"]
        self.meta = dict["meta"]
        self.queue = queue

    async def handle(self):
        try:
            handle_func = self.handlers[self.queue]
            return await handle_func(**self.ctx)
        except Exception as exc:
            stats.errors += 1 # Record new error
            stats.excs.append(exc)
            return exc

# Run the task
if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(main())

        # we enter a never-ending loop that waits for data and runs
        # callbacks whenever necessary.
        print(" [*] Starting Fates List RabbitMQ Worker. To exit press CTRL+C")
        loop.run_forever()
    except KeyboardInterrupt:
        try:
            asyncio.get_event_loop().run_until_complete(rabbitmq.disconnect())
        except:
            pass
        print("RabbitMQ worker down!")
