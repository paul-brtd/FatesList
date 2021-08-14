import builtins
import asyncio
from modules.core.system import setup_db, setup_discord
from fastapi import FastAPI
from config import worker_key
from lynxfall.utils.fastapi import include_routers
from lynxfall.rabbit.core.process import run_worker, disconnect_worker
from .ipc import runipc

app = FastAPI(title="Management API", root_path="/api/admin")

@app.on_event("startup")
async def startup():
    discord = setup_discord()
    db = await setup_db()
    app.state.discord = discord["main"]
    app.state.postgres, app.state.redis = db["postgres"], db["redis"]
    include_routers(app, "admin", "modules/admin/routers")
    asyncio.create_task(runipc(app.state.redis, app.state.discord))
    async def _start(state, logger):
        state.redis = db["redis"]
        state.rabbit = db["rabbit"]
        state.postgres = db["postgres"]
        state.discord = discord["main"]

        # TODO: Get rid of builtins completely
        builtins.db = state.postgres
        builtins.redis_db = state.redis
        builtins.rabbitmq_db = state.rabbit
        builtins.client = builtins.dclient = state.client = state.dclient = state.discord
        logger.info("RabbitMQ startup is done!")

    async def _stop(state, logger):
        logger.info("Rabbit has exited")

    async def _prepare(state, logger):
        return await state.discord.wait_until_ready()

    async def _stub(*_, **__):
        pass

    asyncio.create_task(
        run_worker(
            worker_key=worker_key, 
            backend_folder="modules/admin/rabbit", 
            on_startup = _start, 
            on_prepare = _prepare,
            on_stop = _stop,
            on_error = _stub
        )
    )

@app.on_event("shutdown")
async def shutdown():
    await app.state.redis.publish("_worker", "RESTART IPC")
