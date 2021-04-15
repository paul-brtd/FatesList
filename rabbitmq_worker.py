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
import time
from rabbitmq.backends.add_bot import add_bot_backend
from rabbitmq.backends.edit_bot import edit_bot_backend

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

async def main():
    asyncio.create_task(client.start(TOKEN_MAIN))
    builtins.rabbitmq = await connect_robust(
        f"amqp://fateslist:{rabbitmq_pwd}@127.0.0.1/"
    )
    builtins.db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    builtins.redis_db = await aioredis.from_url('redis://localhost', db = 1)
    # Creating a channel for edit
    channel_edit = await rabbitmq.channel()
    # Declaring queue
    queue_edit = await channel_edit.declare_queue("edit_bot_queue", durable=True)

    # Creating a channel for add
    channel_add = await rabbitmq.channel()
    # Declaring queue
    queue_add = await channel_edit.declare_queue("add_bot_queue", durable=True)

    await queue_edit.consume(edit_bot)
    await queue_add.consume(add_bot)

async def add_bot(message: IncomingMessage):
    """
    Add Bot Callback
    """
    print("Add Bot Called")
    queue = BotQueueData(orjson.loads(message.body))
    await queue.add("add_bot_queue")
    message.ack()

async def edit_bot(message: IncomingMessage):
    """
    Edit Bot Callback
    """
    print("Edit Bot called")
    queue = BotQueueData(orjson.loads(message.body))
    await queue.add("edit_bot_queue")
    message.ack()


class BotQueueData():
    def __init__(self, dict):
        if "creation" not in dict.keys():
            self.creation = time.time()
        self.__dict__.update(dict)
    
    async def add(self, queue):
        if queue == "edit_bot_queue":
            await edit_bot_backend(int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.tags, self.extra_owners, self.creation, self.invite, self.webhook, self.vanity, self.github, self.features, self.html_long_description, self.webhook_type, self.css, self.donate, self.privacy_policy, self.nsfw) # Add edit bot to queue as background task
        elif queue == "add_bot_queue":
            await add_bot_backend(int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.tags, self.extra_owners, self.creation, self.invite, self.features, self.html_long_description, self.css, self.donate, self.github, self.webhook, self.webhook_type, self.vanity, self.privacy_policy, self.nsfw) # Add bot to queue as background task


# Run the task
if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(main())

        # we enter a never-ending loop that waits for data and runs
        # callbacks whenever necessary.
        print(" [*] Waiting for messages. To exit press CTRL+C")
        loop.run_forever()
    except:
        asyncio.get_event_loop().run_until_complete(rabbitmq.close())
        print("RabbitMQ worker down!")
