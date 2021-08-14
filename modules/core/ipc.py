import orjson
import uuid
import time
import asyncio
from loguru import logger

async def redis_ipc(redis, cmd, msg = None, timeout=30):
    cmd_id = uuid.uuid4()
    if msg:
        await redis.set(f"msg-{cmd_id}", orjson.dumps(msg), nx=True, ex=30)
    await redis.publish("_worker", f"{cmd_id} {cmd}")
    start_time = time.time()
    while time.time() - start_time < timeout:
        await asyncio.sleep(0)
        data = await redis.get(f"cmd-{cmd_id}")
        if data is None:
            continue
        return data
    return None      
