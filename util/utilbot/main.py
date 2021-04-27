import discord
from discord.ext.commands import Bot, AutoShardedBot
import aiosqlite # For repl
from tortoise import Tortoise, run_async
import os
import aerich
import sys
import asyncpg
import asyncio
import aioredis
import builtins
sys.path.append("../..")
from config import pg_user, pg_pwd, TOKEN_MAIN, bots_role, bot_dev_role, owner
intents = discord.Intents.default()
intents.members = True
intents.typing = False
class ASB(AutoShardedBot):
    async def is_owner(self, user: discord.User):
        if user.id == owner:
            return True
        return False


# Set the roles in client
client = ASB(command_prefix = "fl!", intents = intents)

client.load_extension("jishaku")
client.bots_role = bots_role
client.bot_dev_role = bot_dev_role


async def setup_db():
    fldb = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    builtins.redis_db = await aioredis.from_url('redis://localhost', db = 1)
    return fldb

async def init():
    # Here we create a SQLite DB using file "db.sqlite3"
    #  also specify the app name of "models"
    #  which contain models from "models"
    await Tortoise.init(
        
        db_url=f'sqlite://prod.db',
        modules={'models': ['models']}
    )
    await Tortoise.generate_schemas()
    
@client.event
async def on_ready():
    print(client.user)
    await init()
    client.fldb = await setup_db()
    try:
        while True:
            await asyncio.sleep(3)
    except:
        await Tortoise.close_connections()

# Add in all cogs
for f in os.listdir("cogs"):
    if not f.startswith("_") or f.startswith("."):
        path = "cogs." + f.replace(".py", "")
        print("Discord: Loading " + f.replace(".py", "") + " with path " + path)
        client.load_extension(path)

if __name__ == "__main__":
    client.run(TOKEN_MAIN)
