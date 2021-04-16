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

# Import all needed backends
from rabbitmq.backends.bot_add import bot_add_backend
from rabbitmq.backends.bot_edit import bot_edit_backend
from rabbitmq.backends.bot_delete import bot_delete_backend

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

async def new_task(queue_name, friendly_name):
    _channel = await rabbitmq.channel()
    _queue = await _channel.declare_queue(queue_name, durable = True) # Function to handle our queue
    
    async def _task(message: IncomingMessage):
        """RabbitMQ Queue Function"""
        print(f"{friendly_name} called")
        _queue_data = BotQueueData(orjson.loads(message.body))
        await _queue_data.add(queue_name)
        message.ack()

    await _queue.consume(_task)

async def main():
    """
    Main worker function
    """
    asyncio.create_task(client.start(TOKEN_MAIN))
    builtins.rabbitmq = await connect_robust(
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
    print("Ready!")

class BotQueueData():
    def __init__(self, dict):
        self.__dict__.update(dict)
    
    async def add(self, queue):
        if queue == "bot_edit_queue": # Edit Backend
            await bot_edit_backend(int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.tags, self.extra_owners, self.creation, self.invite, self.webhook, self.vanity, self.github, self.features, self.long_description_type, self.webhook_type, self.css, self.donate, self.privacy_policy, self.nsfw) # Add edit bot to queue as background task
        elif queue == "bot_add_queue": # Add Backend
            await bot_add_backend(int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.tags, self.extra_owners, self.creation, self.invite, self.features, self.long_description_type, self.css, self.donate, self.github, self.webhook, self.webhook_type, self.vanity, self.privacy_policy, self.nsfw) # Add bot to queue as background task
        elif queue == "bot_delete_queue":
            await bot_delete_backend(int(self.user_id), self.bot_id)
        else:
            raise ValueError("No queue found")

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
