from rabbitmq.core import *
import asyncio
import orjson
import builtins

async def backend(json, **kwargs):
    print("Stub")

class PIDRecorder():
    def __init__(self):
        self.pids = []

    def record(self, pid):
        if pid in self.pids:
            return
        self.pids.append(pid)
        self.pids.sort()

    def remove(self, pid):
        try:
            pid_index = self.pids.index(pid)
        except ValueError:
            return
        del self.pids[pid_index]

    def worker_amt(self):
        return len(self.pids)

    def reset(self):
        self.pids = []

async def status(pidrec):
    pubsub = redis_db.pubsub()
    await pubsub.subscribe("_worker")
    flag = True
    async for msg in pubsub.listen():
        if flag:
            await redis_db.publish("_worker", "UP RMQ 0") # Announce that we are up
            flag = False
        print(msg)
        if msg is None or type(msg.get("data")) != bytes:
            continue
        msg = tuple(msg.get("data").decode("utf-8").split(" "))
        match msg:
            case ("UP", ("RMQ" | "WORKER") as tgt, pid, reload, worker_amt) if pid.isdigit() and reload.isdigit() and worker_amt.isdigit():
                logger.info(f"{tgt} {pid} is now up with reload mode {reload}. Amount of workers is {worker_amt}")
                pidrec.record(int(pid)) if tgt == "WORKER" else None
                if pidrec.worker_amt() > int(worker_amt) and tgt == "WORKER":
                    logger.warning(f"Invalid worker {worker_amt} with pid {pid} added. Restting config and publishing REGET")
                    pidrec.reset()
                    await asyncio.sleep(1)
                    await redis_db.publish("_worker", "REGET WORKER INVALID_STATE")

            case ("DOWN", ("RMQ" | "WORKER") as tgt, pid) if pid.isdigit():
                logger.info(f"{tgt} {pid} is now down")
                pidrec.remove(int(pid)) if tgt == "RMQ" else None
            case _:
                logger.warning(f"Unhandled message {msg}")

async def prehook(*args, **kwargs):
    builtins.pidrec = PIDRecorder()
    asyncio.create_task(status(pidrec))

class Config:   
    queue = "_worker"
    name = "Worker Handler" 
    descriprion = "Handle Workers (PIDs right now but may be increased in future)"
    pre = prehook
