"""
    Deletes all user data and sets a deleted and banned flag to prevent login. Also removes user from extra owner in all bots, removes user from bot stats and vote timestamps

    Usage:
    Enter util folder using cd util/
    Run python
    
    import deleteuserdata
    deleteuserdata.run(USER_Id)
"""
import asyncpg, asyncio, uvloop, aioredis
from config import rabbitmq_pwd
from aio_pika import *


async def main():
    rabbitmq = await connect_robust(
        f"amqp://fateslist:{rabbitmq_pwd}@127.0.0.1/"
    )
    # Creating a channel
    channel = await rabbitmq.channel()

    # Declaring queue
    queue_eb = await channel.declare_queue("edit_bot_queue", durable=True)
    await queue.consume(on_message)

async def on_message(message: IncomingMessage):
    """
    on_message doesn't necessarily have to be defined as async.
    Here it is to show that it's possible.
    """
    print(" [x] Received message %r" % message)
    print("Message body is: %r" % message.body)
    print("Before sleep!")
    await asyncio.sleep(5)  # Represents async I/O operations
    print("After sleep!")
    message.ack()


# Run the task
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())

    # we enter a never-ending loop that waits for data and runs
    # callbacks whenever necessary.
    print(" [*] Waiting for messages. To exit press CTRL+C")
    loop.run_forever()

