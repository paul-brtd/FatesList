from .imports import *

Websocket = WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.fl_loaded = False

    async def connect(self, websocket: WebSocket, api: bool = True):
        await websocket.accept()
        websocket.bots = []
        websocket.tasks = {}
        websocket.authorized = False
        websocket.manager_bot = False
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        # Unsubscribe from pubsub
        try:
            if websocket.pubsub:
                await websocket.pusub.unsubscribe()
        except Exception:
            pass
        try:
            await websocket.close(code=4005)
        except Exception:
            pass
        try:
            self.active_connections.remove(websocket)
        except Exception:
            pass
        # Delete stale websocket credentials
        websocket.bots = [] # Bot ID
        websocket.tasks = {}
        websocket.manager_bot = False
        websocket.authorized = False

    async def send_personal_message(self, message, websocket: WebSocket):
        i = 0
        if websocket not in self.active_connections:
            await manager.disconnect(websocket)
            return False
        while i < 6: # Try to send message 5 times
            try:
                await websocket.send_json(message)
                i = 6
            except:
                if i == 5:
                    # Stop all websocket tasks in websocket.tasks
                    for task_id in websocket.tasks.keys():
                        await websocket.tasks[task_id].cancel()
                        del websocket.tasks[task_id]
                    await manager.disconnect(websocket)
                    return False
                else:
                    i+=1
        return True

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_json(message)

async def ws_close(websocket: WebSocket, code: int):
    websocket.authorized = False
    try:
        return await websocket.close(code=code)
    except:
        return

def ws_identity_payload():
    return {
        "m": {
            "e": enums.APIEvents.ws_identity, 
            "t": [enums.APIEventTypes.auth_token, enums.APIEventTypes.auth_manager_key], 
            "ts": time.time(), 
            "eid": str(uuid.uuid4())
        },
        "ctx": {
        }
    }

async def ws_kill(manager: ConnectionManager, websocket: Websocket, type, code):
    await manager.send_personal_message({
        "m": {
            "e": enums.APIEvents.ws_kill,
            "t": type,
            "ts": time.time(),
            "eid": str(uuid.uuid4())
        }
    }, websocket)
    return await ws_close(websocket, code = code)

async def ws_kill_invalid(manager: ConnectionManager, websocket: Websocket):
    return await ws_kill(manager, websocket, enums.APIEventTypes.ws_invalid, 4000)

async def ws_kill_no_auth(manager: ConnectionManager, websocket: Websocket):
    return await ws_kill(manager, websocket, enums.APIEventTypes.ws_no_auth, 4004)
