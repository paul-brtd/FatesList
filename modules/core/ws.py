from modules.models.enums import WSCloseCode
from .imports import *

Websocket = WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.fl_loaded = False

    async def connect(self, websocket: WebSocket, api: bool = True):
        await websocket.accept()
        websocket.closed = False
        websocket.bots = []
        websocket.tasks = {}
        websocket.pubsub = None
        websocket.authorized = False
        websocket.event_filter = None
        websocket.identified = False
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket, code: int = 4005):
        websocket.authorized = False
        websocket.closed = True
        
        # Unsubscribe from pubsub
        try:
            if websocket.pubsub:
                await websocket.pubsub.unsubscribe()
                websocket.pubsub = None
        except Exception:
            websocket.pubsub = None
        
         # Stop all websocket tasks in websocket.tasks
        try:
            for task_id in websocket.tasks.keys():
                await websocket.tasks[task_id].cancel()
                del websocket.tasks[task_id]
        except Exception:
            websocket.tasks = {}
        
        
        # Kill the websocket
        try:
            await websocket.close(code=code)
        except Exception:
            pass
        
        # Remove from active connections
        try:
            self.active_connections.remove(websocket)
        except Exception:
            pass
        
        # Delete stale websocket credentials
        websocket.bots = [] # Bot ID
        websocket.tasks = {}
        websocket.authorized = False
        websocket.event_filter = None
        websocket.identified = False

    def identify(self, websocket):
        """Helper function to finish auth, call this always after auth"""
        websocket.authorized = True
        websocket.identified = True
        
    async def send_personal_message(self, message, websocket: WebSocket):
        # Do not allow sending to unauthorized sources unless websocket.identified is False
        if not websocket.authorized and websocket.identified:
            return await ws_close(websocket, 4007)
        
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
                    await manager.disconnect(websocket)
                    return False
                else:
                    i+=1
        return True

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_json(message)

async def ws_close(websocket: WebSocket, code: int):
    if not websocket.closed:
        await manager.disconnect(websocket, code = code)

def ws_identity_payload():
    return {
        "m": {
            "e": enums.APIEvents.ws_identity, 
            "t": enums.APIEventTypes.auth_token, 
            "ts": time.time(), 
            "eid": str(uuid.uuid4())
        },
        "ctx": {
        }
    }

async def ws_kill(manager: ConnectionManager, websocket: Websocket, type, code, ratelimited = []):
    await manager.send_personal_message({
        "m": {
            "e": enums.APIEvents.ws_kill,
            "t": type,
            "ts": time.time(),
            "eid": str(uuid.uuid4()),
        },
        "ctx": {
            "rl": ratelimited    
        }
    }, websocket)
    return await ws_close(websocket, code = code)

async def ws_kill_invalid(manager: ConnectionManager, websocket: Websocket, ratelimited = []):
    return await ws_kill(manager, websocket, enums.APIEventTypes.ws_invalid, WSCloseCode.InvalidConn, ratelimited = ratelimited)

async def ws_kill_no_auth(manager: ConnectionManager, websocket: Websocket, ratelimited = [], code = None):
    return await ws_kill(manager, websocket, enums.APIEventTypes.ws_no_auth, code = code if code else WSCloseCode.InvalidAuth, ratelimited = ratelimited)
