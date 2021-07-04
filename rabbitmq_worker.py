from lynxfall.rabbit.launcher import run
from modules.core.system import setup_discord, setup_db
from config import TOKEN_MAIN
from config import worker_key
import asyncio
import builtins
  
async def on_startup(state, logger):
    """Function that will be executed on startup"""
    dbs = await setup_db()
    state.__dict__.update(dbs)
    discord = setup_discord()
    state.client = discord[0]
    asyncio.create_task(state.client.start(TOKEN_MAIN))
    # For unfortunate backward compatibility
    builtins.db = state.postgres
    builtins.redis_db = state.redis
    builtins.rabbitmq_db = state.rabbit
    builtins.client = state.client
    
async def on_prepare(state, logger):
    """Function that will prepare our worker"""
    return await state.client.wait_until_ready()

async def on_stop(state, logger):
    """Function that will run on stop"""

async def on_error(state, logger, message, exc, exc_type, exc_context):
    pass

run(worker_key = worker_key, backend_folder = "modules/rabbitmq", on_startup = on_startup, on_prepare = on_prepare, on_stop = on_stop, on_error = on_error)
