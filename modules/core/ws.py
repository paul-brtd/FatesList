from .imports import *

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.fl_loaded = False

    async def connect(self, websocket: WebSocket, api: bool = True):
        await websocket.accept()
        websocket.api_token = []
        websocket.bot_id = []
        websocket.authorized = False
        websocket.manager_bot = False
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        try:
            await websocket.close(code=4005)
        except:
            pass
        self.active_connections.remove(websocket)

        # Delete stale websocket credentials
        websocket.api_token = []
        websocket.bot_id = [] # Bot ID
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
                    await manager.disconnect(websocket)
                    return False
                else:
                    i+=1

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_json(message)

async def ws_close(websocket: WebSocket, code: int):
    try:
        return await websocket.close(code=code)
    except:
        return
