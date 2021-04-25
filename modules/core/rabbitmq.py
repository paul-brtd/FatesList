from .imports import orjson, aio_pika

async def add_rmq_task(queue_name: str, data: dict):
    """
    Add RabbitMQ Task
    """
    channel = await rabbitmq_db.channel()
    await channel.set_qos(prefetch_count=1)
    await channel.default_exchange.publish(
        aio_pika.Message(orjson.dumps(data), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=queue_name
    )
