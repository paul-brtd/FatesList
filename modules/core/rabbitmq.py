from .imports import orjson, aio_pika
from copy import deepcopy

RMQ_META = {
    "pv": 1, # Protocol Version
    "dbg": True, # Debug Mode
    "auth": "", # If/when we do multi server stuff
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
        ret = meta["ret"]
    else:
        ret = str(uuid.uuid4())
        meta["ret"] = ret
    await  add_rmq_task(queue_name, data, **meta)
    tries = 0
    while tries < 100:
        ret = await redis_db.get(f"rabbit-{ret}")
        if not ret:
            await asyncio.sleep(1) # Wait for one second before retrying
            tries += 1
            continue
        return True, orjson.loads(ret)
    return False, ret # We didnt get anything
