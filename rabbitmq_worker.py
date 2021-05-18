"""RabbitMQ worker"""
import asyncio
from rabbitmq.core.process import run_worker, disconnect_worker

# Run the task
if __name__ == "__main__":
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.create_task(run_worker())
        #loop.create_task(connect(start_time))

        # we enter a never-ending loop that waits for data and runs
        # callbacks whenever necessary.
        loop.run_forever()
    except KeyboardInterrupt:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(disconnect_worker())
        except:
            pass
