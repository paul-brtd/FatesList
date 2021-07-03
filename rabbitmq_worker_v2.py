from lynxfall.rabbit import run
from modules.core.system import setup_discord, setup_db
from config import worker_key
import builtins
  
async def startup_func(state, logger):
    """Function that will be executed on startup"""
    state |= await setup_db()
    discord = await setup_discord()
    state.client = discord[0]
    
    # For unfortunate backward compatibility
    builtins.db = state["postgres"]
    builtins.redis_db = state["redis"]
    builtins.rabbitmq_db = state["rabbit"]
    builtins.client = state["client"]
    
async def prepare_func(state, logger):
    """Function that will prepare our worker"""
    return await state.client.wait_until_ready()

run(worker_key = worker_key, backend_folder = "rabbitmq/backend", startup_func = startup_func, prepare_func = prepare_func)
