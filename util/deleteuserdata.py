"""
    Delete data of a user

    Usage:
    Enter util folder using cd util/
    Run python
    
    import deleteuserdata
    deleteuserdata.run(USER_Id)
"""
import asyncio
import sys

import aioredis
import asyncpg
import uvloop

sys.path.append("..")
from config import *


async def _delud(user_id: int):
    db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    await db.execute("DELETE FROM users WHERE user_id = $1", user_id)
    await db.execute("INSERT INTO users (user_id, vote_epoch) VALUES ($1, NOW())", user_id) # INSERT minimal data to prevent abuse
    bots = await db.fetch(
        "SELECT DISTINCT bots.bot_id FROM bots INNER JOIN bot_owner ON bot_owner.bot_id = bots.bot_id WHERE bot_owner.owner = $1 AND bot_owner.main = true", 
        user_id
    )
    for bot in bots:
        await db.execute("DELETE FROM bots WHERE bot_id = $1", bot["bot_id"])
    votes = await db.fetch("SELECT bot_id from bot_voters WHERE user_id = $1", user_id)
    for vote in votes:
        await db.execute("UPDATE bots SET votes = votes - 1 WHERE bot_id = $1", vote["bot_id"])
    await db.execute("DELETE FROM bot_voters WHERE user_id = $1", user_id)

    redis_db = await aioredis.from_url('redis://localhost', db = 1)
    await redis_db.hdel(str(user_id), 'cache')
    await redis_db.hdel(str(user_id), 'ws')
    await redis_db.close()

# Run the task
def run(user_id):
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(_delud(user_id))
