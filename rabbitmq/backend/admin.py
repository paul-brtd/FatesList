from modules.core import *
import modules.models.enums as enums
import discord
from config import *
import asyncio
from termcolor import cprint
from rabbitmq.core import *

class Config:
    queue = "_admin"
    name = "Admin Task"
    description = "Perform/Evaluate commands in RabbitMQ worker for debugging"

async def backend(json, **kwargs):
    if json["meta"].get("op"):
        # Handle admin operations
        rc = []
        err = []
        ops = json["meta"]["op"]
        if isinstance(ops, str):
            ops = [ops]
        for op in ops:
            _ret, _err = exec_op(op)
            err.append(_err)
            rc.append(_ret)
        return (rc, err)
    return None

backend.__ack_all__ = True
