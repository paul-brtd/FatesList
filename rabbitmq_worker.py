from lynxfall.rabbit.launcher import run
from modules.core.system import setup_discord, setup_db
from config import TOKEN_MAIN
from config import worker_key
import asyncio
import builtins
  
async def startup_func(state, logger):
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
    
async def prepare_func(state, logger):
    """Function that will prepare our worker"""
    return await state.client.wait_until_ready()

run(worker_key = worker_key, backend_folder = "modules/rabbitmq", startup_func = startup_func, prepare_func = prepare_func)
