from lynxfall.rabbitmq import run
from modules.core.system import setup_discord, setup_db
import builtins
  
async def startup_func(logger):
    """Function that will be executed on startup"""
    state = await setup_db()
    builtins.db = state["postgres"]
    builtins.redis_db = state["redis"]
    builtins.rabbitmq_db = state["rabbit"]
