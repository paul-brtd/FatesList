import orjson
import uuid
import time
import asyncio
from loguru import logger

async def redis_ipc_new(redis, cmd, msg = None, timeout=30, args: list = None):
    args = [] if not args else args
    cmd_id = str(uuid.uuid4())
    if msg:
        msg_id = str(uuid.uuid4())
        await redis.set(msg_id, orjson.dumps(msg), nx=True, ex=30)
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

    data = await wait(cmd_id)
    return data if data else None

async def redis_ipc(redis, cmd, msg = None, timeout=30, both = False, args: list = []):
    cmd_id = str(uuid.uuid4())
    print(cmd_id)
    if msg:
        await redis.set(f"msg-{cmd_id}", orjson.dumps(msg), nx=True, ex=30)
    await redis.publish("_worker", f"{cmd_id} {cmd}")
    if both:
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

    if both:
        data2 = await wait(f"cmd-{cmd_id}")
        data = await wait(cmd_id)
        if not data2 or not data:
            return None
        return data, data2
    else:
        data = await wait(f"cmd-{cmd_id}")
    return data if data else None     
