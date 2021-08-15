import asyncio
import builtins
import time

import orjson
import discord

from modules.core import *
from config import staff_roles


class PIDRecorder():
    def __init__(self):
        self.pids = []
        self.session_id = None

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
        self.session_id = None

    def list(self):
        return self.pids

async def catworker(redis, client, pidrec):
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"_worker")
    flag = True
    status_dict = {
        "online": 1,
        "offline": 2,
        "idle": 3,
        "dnd": 4
    }
    async for msg in pubsub.listen():
        if flag:
            await redis.publish(f"_worker", "NOSESSION UP RMQ 0") # Announce that we are up
            flag = False
        if msg is None or type(msg.get("data")) != bytes:
            continue
        msg = tuple(msg.get("data").decode("utf-8").split(" "))
        
        match msg:
            case ("RESTART", "IPC"):
                pidrec.reset()

            case (session_id, "UP", ("RMQ" | "WORKER") as tgt, pid, reload, worker_amt) if pid.isdigit() and reload.isdigit() and worker_amt.isdigit():
            
                logger.info(f"{tgt} {pid} is now up with reload mode {reload}. Amount of workers is {worker_amt}")

                if not pidrec.session_id:
                    pidrec.session_id = session_id

                elif session_id != pidrec.session_id:
                    # Assume new session
                    logger.info("Made new worker session due to new session state")
                    pidrec.reset()
                    pidrec.session_id = session_id

                pidrec.record(int(pid)) if tgt == "WORKER" else None

                if pidrec.worker_amt() > int(worker_amt) and tgt == "WORKER":
                    logger.warning(f"Invalid worker {worker_amt} with pid {pid} added. Restting config and publishing REGET")
                    pidrec.reset()
                    await asyncio.sleep(1)
                    await redis.publish(f"_worker", f"{pidrec.session_id} REGET WORKER INVALID_STATE")

                if pidrec.worker_amt() == int(worker_amt) and tgt == "WORKER":
                    logger.success("All workers are now up")
                    await asyncio.sleep(1)
                    worker_pids = " ".join([str(pid) for pid in pidrec.list()])
                    await redis.publish("_worker", f"{pidrec.session_id} FUP {worker_pids}")

            case ("DOWN", ("RMQ" | "WORKER") as tgt, pid) if pid.isdigit():
                logger.info(f"{tgt} {pid} is now down")
                pidrec.remove(int(pid)) if tgt == "RMQ" else None
           
            case (cmd_id, "GETCH", uid) if uid.isdigit():
                """Getch a member returning 0 if not found, -1 if fail or a user otherwise"""
                async def _getch(uid):
                    uid = int(uid)
                    try:
                        user = client.get_user(uid) or await client.fetch_user(uid)
                    except discord.NotFound:
                        await redis.set(f"cmd-{cmd_id}", 0, nx=True, ex=30)
                        return
                    except Exception as exc:
                        await redis.set(f"cmd-{cmd_id}", -1, nx=True, ex=30)
                        logger.exception("A error has occurred")
                        return exc

                    if user.mutual_guilds:
                        in_main_server = True
                        try:
                            user = user.mutual_guilds[0].get_member(uid)
                            status = status_dict.get(str(user.status), 0)
                        except Exception:
                            status = 0
                    else:
                        status = 0
                        in_main_server = False
                   
                    json = {
                        "username": user.name,
                        "avatar": user.avatar.url,
                        "disc": user.discriminator,
                        "bot": user.bot,
                        "status": status,
                        "main_server": in_main_server
                    }
                    await redis.set(f"cmd-{cmd_id}", orjson.dumps(json), nx=True, ex=30)
                    return

                asyncio.create_task(_getch(uid))

            case (cmd_id, "ROLES", uid) if uid.isdigit():
                """Get roles returing 0 if member not found or the list of roles"""
                async def _roles(uid):
                    # Since the main bot will only be in one server, we can just use client.guilds[0]                    
                    user = client.guilds[0].get_member(int(uid))
                    if not user:
                        await redis.set(f"cmd-{cmd_id}", 0, nx=True, ex=30)
                        return
                    roles = orjson.dumps([role.id for role in user.roles])
                    await redis.set(f"cmd-{cmd_id}", roles, nx=True, ex=30)
                    return

                asyncio.create_task(_roles(uid))
            
            case (cmd_id, "PING"):
                """Returns "PONG Vx Y" where x is the ipc protocol version and Y is the degraded state value (1=degraded)."""
                async def _ping():
                    v = "V2"
                    degraded = await redis.get("degrade-state")
                    degraded = 1 if degraded else 0
                    await redis.set(f"cmd-{cmd_id}", f"PONG {v} {degraded}", nx=True, ex=30)
                asyncio.create_task(_ping())

            case (cmd_id, "SENDMSG", channel_id) if channel_id.isdigit():
                """
                Sends a message to channel with channel_id. 

                Returns 0 if message not found in redis or not json serializable or channel not found or message failed to send, 1 is successful
                """
                async def _sendmsg(cmd_id, channel_id):
                    dat = await redis.get(f"msg-{cmd_id}")
                    if not dat:
                        await redis.set(f"cmd-{cmd_id}", 0, nx=True, ex=30)
                        return
                    try:
                        dat = orjson.loads(dat)
                    except Exception:
                        await redis.set(f"cmd-{cmd_id}", 0, nx=True, ex=30)
                        return

                    channel = client.get_channel(int(channel_id))
                    if not channel:
                        await redis.set(f"cmd-{cmd_id}", 0, nx=True, ex=30)
                        return
                    
                    try:
                        if dat.get("embed"):
                            embed = discord.Embed.from_dict(dat.get("embed"))
                        else:
                            embed = None

                        f = dat.get("file")
                        if f:
                            f_id = f["name"]
                            f_data = f.get("content", "No file content sent")
                            fl_file = discord.File(io.BytesIO(bytes(f_data, 'utf-8')), f_id)
                        else:
                            fl_file = None
                        await channel.send(content=dat.get("content"), embed=embed, file=fl_file)
                    except Exception as exc:
                        logger.exception("IPC error")
                        await redis.set(f"cmd-{cmd_id}", 0, nx=True, ex=30)
                        return
                    
                    await redis.set(f"cmd-{cmd_id}", 1, nx=True, ex=30)
                    return

                asyncio.create_task(_sendmsg(cmd_id, channel_id))
            case _:
                logger.debug(f"Got msg {msg}")
                
async def runipc(redis, client):
    pidrec = PIDRecorder()
    asyncio.create_task(catworker(redis, client, pidrec))
