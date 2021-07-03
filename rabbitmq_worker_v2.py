from lynxfall.rabbit import run
from modules.core.system import setup_discord, setup_db
import builtins
  
async def startup_func(logger):
    """Function that will be executed on startup"""
    state = await setup_db()
    discord = await setup_discord()
    state["client"] = discord[0]
    
    # For unfortunate backward compatibility
    builtins.db = state["postgres"]
    builtins.redis_db = state["redis"]
    builtins.rabbitmq_db = state["rabbit"]
    builtins.client = state["client"]

    return state
