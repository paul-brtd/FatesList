import orjson
import uuid
import time
import asyncio
from loguru import logger
import warnings


async def redis_ipc_new(redis, cmd, msg = None, timeout=30, args: list = None):
    args = [] if not args else args
    cmd_id = str(uuid.uuid4())
    if msg:
        msg_id = str(uuid.uuid4())
        await redis.set(msg_id, orjson.dumps(msg), ex=30)
        args.append(msg_id)
    args = " ".join(args)
    if args:
        await redis.publish("_worker_fates", f"{cmd} {cmd_id} {args}")
    else:
        await redis.publish("_worker_fates", f"{cmd} {cmd_id}")
    
    async def wait(id):
        start_time = time.time()
        while time.time() - start_time < timeout:
            await asyncio.sleep(0)
            data = await redis.get(id)
            if data is None:
                continue
            return data

    if timeout:
        data = await wait(cmd_id)
    else:
        return None
    return data if data else None

# Deprecated
async def redis_ipc(redis, cmd, msg = None, timeout=30, both = False, args: list = []):
    warnings.warn("This function is deprecated. Use redis_ipc_new instead!")
    return await redis_ipc_new(redis, cmd, msg = msg, timeout=timeout, args = args)