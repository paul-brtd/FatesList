# Migrate extra owners to seperate db
import asyncpg, asyncio
from config import *
import fastapi
app = fastapi.FastAPI()

async def migdb():
    db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    bots = await db.fetch("SELECT queue, banned, bot_id FROM bots")
    for bot in bots:
        print(bot)
        if bot["banned"]:
            queue_state = 2
        elif bot["queue"]:
            queue_state = 1
        else:
            queue_state = 0
        print(queue_state)
        await db.execute("UPDATE bots SET queue_state = $1 WHERE bot_id = $2", queue_state, bot["bot_id"])

@app.on_event("startup")
async def startup():
    await migdb()
