# Migrate extra owners to seperate db
import asyncpg, asyncio
from config import *
import fastapi
app = fastapi.FastAPI()

async def migdb():
    db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    await db.execute("DROP TABLE bot_owner")
    await db.execute("""
CREATE TABLE IF NOT EXISTS bot_owner (
bot_id BIGINT not null,
owner BIGINT,
main BOOLEAN DEFAULT false
);
    """)
    bots = await db.fetch("SELECT owner, extra_owners, bot_id FROM bots")
    for bot in bots:
        print(bot)
        await db.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", bot["bot_id"], bot["owner"], True)
        if bot["extra_owners"] is None:
            continue
        for eo in bot["extra_owners"]:
            await db.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", bot["bot_id"], eo, False)

@app.on_event("startup")
async def startup():
    await migdb()
