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
from rabbitmq.backends.add_bot import add_bot_backend
from rabbitmq.backends.edit_bot import edit_bot_backend
from rabbitmq.backends.delete_bot import delete_bot_backend


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
    await new_task("edit_bot_queue", "Edit Bot")
    await new_task("add_bot_queue", "Add Bot")
    await new_task("delete_bot_queue", "Delete Bot")
    print("Ready!")

class BotQueueData():
    def __init__(self, dict):
        self.__dict__.update(dict)
    
    async def add(self, queue):
        if queue == "edit_bot_queue": # Edit Backend
            await edit_bot_backend(int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.tags, self.extra_owners, self.creation, self.invite, self.webhook, self.vanity, self.github, self.features, self.html_long_description, self.webhook_type, self.css, self.donate, self.privacy_policy, self.nsfw) # Add edit bot to queue as background task
        elif queue == "add_bot_queue": # Add Backend
            await add_bot_backend(int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.tags, self.extra_owners, self.creation, self.invite, self.features, self.html_long_description, self.css, self.donate, self.github, self.webhook, self.webhook_type, self.vanity, self.privacy_policy, self.nsfw) # Add bot to queue as background task
        elif queue == "delete_bot_queue":
            await delete_bot_backend(int(self.user_id), self.bot_id)

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
        asyncio.get_event_loop().run_until_complete(rabbitmq.disconnect())
        print("RabbitMQ worker down!")
