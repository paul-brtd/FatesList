import builtins
import asyncio
from modules.core.system import setup_db, setup_discord
from fastapi import FastAPI
from config import worker_key, TOKEN_DBG
from lynxfall.utils.fastapi import include_routers
from lynxfall.rabbit.core.process import run_worker, disconnect_worker
from .ipc import runipc
from .dbgbot import Manager
from fastapi.exceptions import (HTTPException, RequestValidationError,
                                        ValidationError)
from starlette.exceptions import HTTPException as StarletteHTTPException
from modules.core.error import WebError

app = FastAPI(title="Management API", root_path="/api/admin")

@app.on_event("startup")
async def startup():
    # Setup exception handling
    @app.exception_handler(403)
    @app.exception_handler(404)
    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    @app.exception_handler(500)
    @app.exception_handler(HTTPException)
    @app.exception_handler(Exception)
    @app.exception_handler(StarletteHTTPException)
    async def _fl_error_handler(request, exc):
        return await WebError.error_handler(request, exc, log=True)

    discord = setup_discord()
    db = await setup_db()
    app.state.discord = discord["main"]
    app.state.dbgbot = discord["debug"]
    app.state.dbgbot.load_extension("jishaku")
    app.state.dbgbot.add_cog(Manager(app.state.dbgbot, app))
    asyncio.create_task(app.state.dbgbot.start(TOKEN_DBG))
    app.state.postgres, app.state.redis = db["postgres"], db["redis"]
    include_routers(app, "admin", "modules/dragon/routers")
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
            backend_folder="modules/dragon/rabbit", 
            on_startup = _start, 
            on_prepare = _prepare,
            on_stop = _stop,
            on_error = _stub
        )
    )

@app.on_event("shutdown")
async def shutdown():
    await app.state.redis.publish("_worker", "IPC DOWN")
    await app.state.redis.publish("_worker", "RESTART IPC")
