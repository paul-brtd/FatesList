"""
    RabbitMQ worker
"""
import asyncpg, asyncio, uvloop, aioredis
import sys
sys.path.append("..")
from config import *
from aio_pika import *
import discord
import orjson
import builtins
from copy import deepcopy
from termcolor import colored, cprint

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

async def new_task(queue_name, friendly_name):
    _channel = await rabbitmq_db.channel()
    _queue = await _channel.declare_queue(queue_name, durable = True) # Function to handle our queue
    
    async def _task(message: IncomingMessage):
        """RabbitMQ Queue Function"""
        print(f"{friendly_name} called")
        _task_handler = TaskHandler(orjson.loads(message.body), queue_name)
        rc = await _task_handler.handle()
        if rc:
            cprint(rc, "red")
        else:
            message.ack()

    await _queue.consume(_task)

async def main():
    """
    Main worker function
    """
    asyncio.create_task(client.start(TOKEN_MAIN))
    asyncio.create_task(client_server.start(TOKEN_SERVER))
    builtins.rabbitmq_db = await connect_robust(
        f"amqp://fateslist:{rabbitmq_pwd}@127.0.0.1/"
    )
    builtins.db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    builtins.redis_db = await aioredis.from_url('redis://localhost', db = 1)
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
            await handle_func(**self.ctx)
        except Exception as exc:
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
