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

async def main():
    """
    Main worker function
    """
    builtins.db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    for tag in TAGS.keys():
        await db.execute("INSERT INTO bot_list_tags (id, icon, type) VALUES ($1, $2, 0)", tag, TAGS[tag])
    print("Ready!")

class BotQueueData():
    def __init__(self, dict):
        self.__dict__.update(dict)

    async def add(self, queue):
        if queue == "bot_edit_queue": # Edit Backend
            await bot_edit_backend(int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.tags, self.extra_owners, self.invite, self.webhook, self.vanity, self.github, self.features, self.long_description_type, self.webhook_type, self.css, self.donate, self.privacy_policy, self.nsfw) # Add edit bot to queue as background task
        elif queue == "bot_add_queue": # Add Backend
            await bot_add_backend(int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.tags, self.extra_owners, self.invite, self.features, self.long_description_type, self.css, self.donate, self.github, self.webhook, self.webhook_type, self.vanity, self.privacy_policy, self.nsfw) # Add bot to queue as background task
        elif queue == "bot_delete_queue":
            await bot_delete_backend(int(self.user_id), self.bot_id)
        elif queue == "server_add_queue":
            await server_add_backend(self.user_id, self.guild_id, self.data["name"], self.description, self.long_description_type, self.long_description, self.tags, self.vanity)
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
