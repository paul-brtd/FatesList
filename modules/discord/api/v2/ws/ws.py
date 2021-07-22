from modules.core import *

from ..base import API_VERSION

router = APIRouter(
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Websockets"]
) # No arguments needed for websocket but keep for chat

builtins.manager = ConnectionManager()

async def dispatch_events_old(websocket, bot):
    """Dispatch old events to the requester"""
    if not websocket.authorized:
        return # Stop sending if not authorized 

async def ws_command_handler(websocket):
    """Websocket Command Handling"""
    while True:
        data = await websocket.receive_json()
        if not websocket.authorized:
            return # Stop command handling
        await asyncio.sleep(0) # Ensure other tasks don't mess up
        try:
            # Dispatch old events
            if data["cmd"] == enums.WebSocketCommand.dispatch_old:
                bot = data["id"]
                flag = False
                for auth_bot in websocket.bots:
                    if bot == auth_bot["id"]:
                        # We have a match
                        flag = True
                        websocket.tasks[str(uuid.uuid4())] = asyncio.create_task(dispatch_events_old(websocket, bot)) # Store task in dict
                if not flag:
                    return await ws_kill_no_auth(manager, websocket)
                
            else:
                return await ws_kill_invalid(manager, websocket)
        except Exception:
            return await ws_kill_invalid(manager, websocket)
        
@router.websocket("/api/v2/ws/rtstats")
async def websocket_bot_rtstats_v1(websocket: WebSocket):
    logger.debug("Got websocket connection request. Connecting...")
    await manager.connect(websocket)
    if not websocket.identified:
        logger.debug("Sending IDENTITY to websocket")
        await manager.send_personal_message(ws_identity_payload(), websocket)
        
        try:
            data = await websocket.receive_json()
            logger.debug("Got response from websocket. Checking response...")
            if (data["m"]["e"] != enums.APIEvents.ws_identity_res 
                or enums.APIEventTypes(data["m"]["t"]) not in [enums.APIEventTypes.auth_token]):
                return await ws_kill_invalid(manager, websocket)
        except Exception:
            return await ws_kill_invalid(manager, websocket)

        match data["m"]["t"]:
            case enums.APIEventTypes.auth_token:
                try:
                    auth_dict = data["ctx"]["auth"]
                    event_filter = data["ctx"].get("filter")
                except:
                    return await ws_kill_invalid(manager, websocket) 
                if not isinstance(auth_dict, list): 
                    return await ws_kill_invalid(manager, websocket)
                rl_lst = []
                for bot in auth_dict:
                    if not isinstance(bot, dict):
                        continue
                    id = bot.get("id")
                    token = bot.get("token")
                    if not token or not isinstance(token, str):
                        continue
                    if not id or not isinstance(id, str) or not id.isdigit():
                        continue
                    bid = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1 AND bot_id = $2", token, int(id))
                    if bid:
                        rl = await redis_db.get(f"identity-{id}")
                        if not rl:
                            rl = []
                            exp = {"ex": 60*60*24}
                        else:
                            rl = orjson.loads(rl)
                            exp = {"keepttl": True}
                        if len(rl) > 100: 
                            rl.append(id)
                            continue
                        elif rl and time.time() - rl[-1] > 5 and time.time() - rl[-1] < 65:
                            rl.append(id)
                            continue
                        rl.append(time.time())
                        await redis_db.set(f"identity-{id}", orjson.dumps(rl), **exp)
                        websocket.bots.append(bot)
                if websocket.bots == []:
                    return await ws_kill_no_auth(manager, websocket, ratelimited = rl_lst)
                logger.debug("Authenticated successfully to websocket")
                await manager.send_personal_message({
                    "m": {
                        "e": enums.APIEvents.ws_status, 
                        "eid": str(uuid.uuid4()), 
                        "t": enums.APIEventTypes.ws_ready
                    }, 
                    "ctx": {
                        "bots": [{"id": bot['id'], "ws_api": f"/api/bots/{bot['id']}/ws_events"} for bot in websocket.bots]
                    }
                }, websocket)
                await manager.identify(websocket)
        
    try:
        if isinstance(event_filter, int):
            websocket.event_filter = [event_filter]
        elif not isinstance(event_filter, list):
            websocket.event_filter = None
    
        websocket.pubsub = redis_db.pubsub()
        for bot in websocket.bots:
            await websocket.pubsub.subscribe(f"bot-{bot['id']}")
        websocket.tasks[str(uuid.uuid4())] = asyncio.create_task(ws_command_handler(websocket)) # Begin command handling and add it to tasks list
        
    except Exception:
        return await ws_close(websocket, 4009)
    websocket.tasks[str(uuid.uuid4())] = asyncio.create_task(dispatch_events_new(websocket))
    try:
        while True:
            if not websocket.authorized:
                return
            await asyncio.sleep(0)
    except Exception:
        return await ws_close(websocket, 4008)

async def dispatch_events_new(websocket):
    logger.debug("Running")
    async for msg in websocket.pubsub.listen():
        if not websocket.authorized:
            raise Exception("No longer authorized")
            return
        logger.debug(f"Got message {msg}")
        if msg is None or not isinstance(msg.get("data"), bytes):
            continue
        
        data = orjson.loads(msg.get("data"))
        event_id = list(data.keys())[0]
        event = data[event_id]
        bot_id = msg.get("channel").decode("utf-8").split("-")[1]
        event["m"]["id"] = bot_id
            
        logger.debug(f"Parsing event {event}")
        try:
            if not websocket.event_filter or event["m"]["e"] in websocket.event_filter:
                flag = True
            else:
                flag = False
            
        except Exception as exc:
            flag = False

        if flag:
            logger.debug("Sending event now...")
            rc = await manager.send_personal_message(event, websocket) 
