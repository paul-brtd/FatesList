from .imports import orjson, aio_pika
from copy import deepcopy
from config_secrets import *

# Needed for it to actually work in manager
import uuid
import asyncio

RMQ_META = {
    "pv": 1, # Protocol Version
    "dbg": True, # Debug Mode
    "auth": worker_key, # Worker Key for auth
    "worker": None, # For when we do multi server rabbit
    "op": None, # Any operations that we should run in list format
    "ret": None # The UUID to save returned values to on Redis if wanted
}

async def add_rmq_task(queue_name: str, data: dict, **meta):
    """Add RabbitMQ Task"""
    if meta:
        meta = deepcopy(RMQ_META) | meta
    else:
        meta = RMQ_META
    channel = await rabbitmq_db.channel()
    await channel.set_qos(prefetch_count=1)
    await channel.default_exchange.publish(
    aio_pika.Message(orjson.dumps({"ctx": data, "meta": meta}), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=queue_name
    )

async def add_rmq_task_with_ret(queue_name, data: dict, **meta):
    """Add RabbitMQ Task, wait for it to complete, then get return code from Redis and return it"""
    if "ret" in meta.keys():
        _ret = meta["ret"]
    else:
        _ret = str(uuid.uuid4())
        meta["ret"] = _ret
    await  add_rmq_task(queue_name, data, **meta)
    tries = 0
    while tries < 100:
        ret = await redis_db.get(f"rabbit-{_ret}")
        if not ret:
            await asyncio.sleep(0.5) # Wait for half second before retrying
            tries += 1
            continue
        await redis_db.delete(f"rabbit-{_ret}")
        return True, orjson.loads(ret)
    return False, _ret # We didnt get anything
