from modules.core import *
from ..base import API_VERSION

router = APIRouter(
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Websockets"]
) # No arguments needed for websocket but keep for chat

builtins.manager = ConnectionManager()

@router.websocket("/api/v2/ws/rtstats")
async def websocket_bot_rtstats_v1(websocket: WebSocket):
    logger.debug("Got websocket connection request. Connecting...")
    await manager.connect(websocket)
    if websocket.api_token == [] and not websocket.manager_bot:
        logger.debug("Sending IDENTITY to websocket")
        await manager.send_personal_message(ws_identity_payload(), websocket)
        try:
            data = await websocket.receive_json()
            logger.debug("Got response from websocket. Checking response...")
            if data["m"]["e"] != enums.APIEvents.ws_identity_res or enums.APIEventTypes(data["m"]["t"]) not in [enums.APIEventTypes.auth_token, enums.APIEventTypes.auth_manager_key]:
                raise TypeError
        except:
            return await ws_kill_invalid(manager, websocket)
        match data["m"]["t"]:
            case enums.APIEventTypes.auth_token:
                try:
                    api_token = data["ctx"]["token"]
                    event_filter = data["ctx"].get("filter")
                except:
                    return await ws_kill_invalid(manager, websocket) 
                if api_token is None or type(api_token) == int or type(api_token) == str:
                    return await ws_kill_invalid(manager, websocket)
                for bot in api_token:
                    bid = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", str(bot))
                    if bid:
                        websocket.api_token.append(api_token)
                        websocket.bot_id.append(bid["bot_id"])
                if websocket.api_token == [] or websocket.bot_id == []:
                    return await ws_kill_no_auth(manager, websocket)
                logger.debug("Authenticated successfully to websocket")
                await manager.send_personal_message({"m": {"e": enums.APIEvents.ws_status, "eid": str(uuid.uuid4()), "t": enums.APIEventTypes.ws_ready}, "ctx": {"bots": [str(bid) for bid in websocket.bot_id]}}, websocket)
            case enums.APIEventTypes.auth_manager_key:
                try:
                    if secure_strcmp(data["ctx"]["key"], test_server_manager_key) or secure_strcmp(data["ctx"]["key"], root_key):
                        websocket.manager_bot = True
                        event_filter = data["ctx"].get("filter")
                    else:
                        return await ws_kill_no_auth(manager, websocket) 
                except:
                    return await ws_kill_invalid(manager, websocket)
                await manager.send_personal_message({"m": {"e": enums.APIEvents.ws_status, "eid": str(uuid.uuid4()), "t": enums.APIEventTypes.ws_ready}, "ctx": None}, websocket)
    try:
        if isinstance(event_filter, int):
            event_filter = [event_filter]
        elif isinstance(event_filter, list):
            pass
        else:
            event_filter = None
        if not websocket.manager_bot:
            ini_events = {}
            for bot in websocket.bot_id:
                events = await redis_db.hget(f"bot-{bot}", key = "ws")
            if events is None:
                events = {} # Nothing
            else:
                try:
                    events = orjson.loads(events)
                except Exception as exc:
                    logger.exception()
                    events = {}
                ini_events[str(bot)] = events
            await manager.send_personal_message({"m": {"e": enums.APIEvents.ws_event, "eid": str(uuid.uuid4()), "t": enums.APIEventTypes.ws_event_multi, "ts": time.time()}, "ctx": ini_events}, websocket)
            pubsub = redis_db.pubsub()
            for bot in websocket.bot_id:
                await pubsub.subscribe("bot_" + str(bot))
        else:
            pubsub = redis_db.pubsub()
            await pubsub.psubscribe("*")
    
        async for msg in pubsub.listen():
            logger.debug(f"Got message {msg} with manager status of {websocket.manager_bot}")
            if msg is None or type(msg.get("data")) != bytes:
                continue
            data = orjson.loads(msg.get("data"))
            event_id = list(data.keys())[0]
            bot_id = msg.get("channel").decode("utf-8").split("-")[1]
            try:
                if not event_filter or data[event_id]["m"]["e"] in event_filter:
                    flag = True
                else:
                    flag = False
            except Exception as exc:
                flag = False
            if flag:
                rc = await manager.send_personal_message({"m": {"e": enums.APIEvents.ws_event, "eid": str(uuid.uuid4()), "t": enums.APIEventTypes.ws_event_single, "ts": time.time(), "id": bot_id}, "ctx": data[event_id]}, websocket)
            else:
                rc = True
            if not rc:
                await ws_close(websocket, 4007)
                return
    except Exception as exc:
        print(exc)
        try:
            await pubsub.unsubscribe()
        except:
            pass
        await ws_close(websocket, 4006)
        raise exc
        await manager.disconnect(websocket)
