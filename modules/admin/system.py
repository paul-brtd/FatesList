from modules.core.system import setup_db, setup_discord
from fastapi import FastAPI
from lynxfall.utils.fastapi import include_routers
from .ipc import runipc
import asyncio

app = FastAPI(title="Management API")

@app.on_event("startup")
async def startup():
    discord = setup_discord()
    db = await setup_db()
    app.state.discord = discord["main"]
    app.state.db, app.state.redis = db["postgres"], db["redis"]
    include_routers(app, "admin", "modules/admin/routers")
    asyncio.create_task(runipc(app.state.redis, app.state.discord))

@app.on_event("shutdown")
async def shutdown():
    await app.state.redis.publish("_worker", "RESTART IPC")
