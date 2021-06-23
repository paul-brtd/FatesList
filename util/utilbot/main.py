import discord
from discord.ext.commands import Bot, AutoShardedBot
import os
import sys
import asyncio
import aioredis
import aio_pika
import builtins
sys.path.append("../..")
from config import TOKEN_MAIN, bots_role, bot_dev_role, owner, rabbitmq_pwd, worker_key
intents = discord.Intents.default()
intents.members = True
intents.typing = False
class ASB(AutoShardedBot):
    async def is_owner(self, user: discord.User):
        if user.id == owner:
            return True
        return False


# Set the roles in client
builtins.client = ASB(command_prefix = "fl!", intents = intents)

client.load_extension("jishaku")
client.bots_role = bots_role
client.bot_dev_role = bot_dev_role


async def setup_db():
    builtins.redis_db = await aioredis.from_url('redis://localhost:12348', db = 1)
    builtins.rabbitmq_db = await aio_pika.connect_robust(
        f"amqp://fateslist:{rabbitmq_pwd}@127.0.0.1/"
    )

@client.event
async def on_ready():
    print(client.user)
    await setup_db()
    try:
        while True:
            await asyncio.sleep(3)
    except:
        await redis_db.close()

# Add in all cogs
for f in os.listdir("cogs"):
    if not f.startswith("_") or f.startswith("."):
        path = "cogs." + f.replace(".py", "")
        print("Discord: Loading " + f.replace(".py", "") + " with path " + path)
        client.load_extension(path)

if __name__ == "__main__":
    client.run(TOKEN_MAIN)
