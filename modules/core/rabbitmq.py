from .imports import orjson, aio_pika

RMQ_META = {
    "pv": 1, # Protocol Version
    "dbg": True, # Debug Mode
    "auth": "", # If/when we do multi server stuff
    "worker": None, # For when we do multi server rabbit
    "op": None # Any operations that we should run in list format
}

async def add_rmq_task(queue_name: str, data: dict, *, meta: dict = RMQ_META):
    """
    Add RabbitMQ Task
    """
    channel = await rabbitmq_db.channel()
    await channel.set_qos(prefetch_count=1)
    await channel.default_exchange.publish(
    aio_pika.Message(orjson.dumps({"ctx": data, "meta": meta}), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=queue_name
    )
