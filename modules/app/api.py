from ..deps import *
from uuid import UUID
from fastapi.responses import HTMLResponse
from typing import List

router = APIRouter(
    prefix = "/api",
    include_in_schema = True
)

class PromoDelete(BaseModel):
    promo_id: Optional[uuid.UUID] = None

class Promo(BaseModel):
    title: str
    info: str

class PromoPatch(Promo):
    promo_id: uuid.UUID

@router.delete("/bots/{bot_id}/promotions", tags = ["API"])
async def delete_promotion(request: Request, bot_id: int, promo: PromoDelete, Authorization: str = Header("INVALID_API_TOKEN")):
    """Deletes a promotion for a bot or deletes all promotions from a bot (WARNING: DO NOT DO THIS UNLESS YOU KNOW WHAT YOU ARE DOING).

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Event ID**: This is the ID of the event you wish to delete. Not passing this will delete ALL events, so be careful
    """
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    id = id["bot_id"]
    if promo.promo_id is not None:
        eid = await db.fetchrow("SELECT id FROM promotions WHERE id = $1", promo.promo_id)
        if eid is None:
            return {"done":  False, "reason": "NO_PROMOTION_FOUND"}
        await db.execute("DELETE FROM promotions WHERE bot_id = $1 AND id = $2", id, promo.promo_id)
    else:
        await db.execute("DELETE FROM promotions WHERE bot_id = $1", id)
    return {"done":  True, "reason": None}

@router.put("/bots/{bot_id}/promotions", tags = ["API"])
async def create_promotion(request: Request, bot_id: int, promo: Promo, Authorization: str = Header("INVALID_API_TOKEN")):
    """Creates a promotion for a bot. Events can be used to set guild/shard counts, enter maintenance mode or to show promotions

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Promotion**: This is the name of the event in question. There are a few special events as well:

    """
    if len(promo.title) < 3:
        return {"done":  False, "reason": "TEXT_TOO_SMALL"}
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    id = id["bot_id"]
    await add_promotion(id, promo.title, promo.info)
    return {"done":  True, "reason": None}

@router.patch("/bots/{bot_id}/promotions", tags = ["API"])
async def edit_promotion(request: Request, bot_id: int, promo: PromoPatch, Authorization: str = Header("INVALID_API_TOKEN")):
    """Edits an promotion for a bot given its promotion ID.

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb

    **Promotion ID**: This is the ID of the promotion you wish to edit 

    """
    if len(promo.title) < 3:
        return {"done":  False, "reason": "TEXT_TOO_SMALL"}
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    id = id["bot_id"]
    pid = await db.fetchrow("SELECT id, events FROM api_event WHERE id = $1", promo.promo_id)
    if eid is None:
        return {"done":  False, "reason": "NO_MESSAGE_FOUND"}
    await db.execute("UPDATE promotions SET title = $1, info = $2 WHERE bot_id = $3", promo.title, promo.info, id)
    return {"done": True, "reason": None}

@router.patch("/bots/{bot_id}/token", tags = ["API"])
async def regenerate_token(request: Request, bot_id: int, Authorization: str = Header("INVALID_API_TOKEN")):
    """Regenerate the API token

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token or clicking APIWeb
    """
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    await db.execute("UPDATE bots SET api_token = $1 WHERE bot_id = $2", get_token(101), id["bot_id"])
    return {"done": True, "reason": None}

@router.get("/bots/random", tags = ["API"])
async def random_bots_api(request: Request):
    random_unp = await db.fetchrow("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false AND banned = false AND disabled = false ORDER BY RANDOM() LIMIT 1") # Unprocessed
    bot = (await get_bot(random_unp["bot_id"])) | dict(random_unp)
    bot["bot_id"] = str(bot["bot_id"])
    bot["servers"] = await human_format(bot["servers"])
    return bot

@router.get("/bots/{bot_id}", tags = ["API"])
async def get_bots_api(request: Request, bot_id: int, Authorization: str = Header("INVALID_API_TOKEN")):
    """Gets bot information given a bot ID. If not found, 404 will be returned. If a proper API Token is provided, sensitive information (System API Events will also be provided)"""
    api_ret = await db.fetchrow("SELECT bot_id AS id, description, tags, html_long_description, long_description, servers AS server_count, shard_count, prefix, invite, invite_amount, owner AS _owner, extra_owners AS _extra_owners, features, bot_library AS library, queue, banned, website, discord AS support, github FROM bots WHERE bot_id = $1", bot_id)
    if api_ret is None:
        return abort(404)
    api_ret = dict(api_ret)
    bot_obj = await get_bot(bot_id)
    api_ret["username"] = bot_obj["username"]
    api_ret["avatar"] = bot_obj["avatar"]
    if api_ret["_extra_owners"] is None:
        api_ret["owners"] = [api_ret["_owner"]]
    else:
        api_ret["owners"] = [api_ret["_owner"]] + api_ret["_extra_owners"]
    api_ret["id"] = str(api_ret["id"])
    if Authorization is not None:
        check = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", str(Authorization))
        if check is None or check["bot_id"] != bot_id:
            sensitive = False
        else:
            sensitive = True
    else:
        sensitive = False
    if sensitive:
        api_ret["sensitive"] = await get_events(bot_id = bot_id)
    else:
        api_ret["sensitive"] = {}
    api_ret["promotions"] = await get_promotions(bot_id = bot_id)
    api_ret["maint"] = await in_maint(bot_id = bot_id)
    api_ret["actions"] = [{"stats": f"https://fateslist.xyz/api/bots/{bot_id}/stats", "method": "POST"}, {"maintenance": f"https://fateslist.xyz/api/bots/{bot_id}/maintenance", "method": "POST"}, {"add_promotion": f"https://fateslist.xyz/api/bots/{bot_id}/promotions", "method": "PUT"}, {"edit_promotion": f"https://fateslist.xyz/api/bots/{bot_id}/promotions", "method": "PATCH"}, {"delete_promotion": f"https://fateslist.xyz/api/bots/{bot_id}/promotions", "method": "DELETE"}, {"regenerate_token": f"https://fateslist.xyz/api/bots/{bot_id}/token", "method": "PATCH"}]
    return api_ret

@router.get("/bots/{bot_id}/votes", tags = ["API"])
async def get_votes_api(request: Request, bot_id: int, user_id: Optional[int] = None, Authorization: str = Header("INVALID_API_TOKEN")):
    """Endpoint to check amount of votes a user has"""
    id = await db.fetchrow("SELECT votes, voters FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    if id["voters"] is None:
        return {"votes": 0, "voted": False}
    if user_id is not None:
        voter_count = len([user for user in id["voters"] if user == user_id])
    else:
        voter_count = id["votes"]
    return {"votes": voter_count, "voted": voter_count != 0}
# TODO
#@router.get("/templates/{code}", tags = ["Core API"])
#async def get_template_api(request: Request, code: str):
#    guild =  await client.fetch_template(code).source_guild
#    return template

class APISGC(BaseModel):
    guild_count: int
    shard_count: int

@router.post("/bots/{bot_id}/stats", tags = ["API"])
async def set_bot_stats_api(request: Request, bot_id: int, api: APISGC, Authorization: str = Header("INVALID_API_TOKEN")):
    """
    This endpoint allows you to set the guild + shard counts for your bot
    """
    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return abort(401)
    await set_guild_shard_count(id["bot_id"], api.guild_count, api.shard_count)
    return {"done": True, "reason": None}
class APISMaint(BaseModel):
    mode: int = 1
    reason: str

@router.post("/bots/{bot_id}/maintenances", tags = ["API"])
async def set_maintenance_mode(request: Request, bot_id: int, api: APISMaint, Authorization: str = Header("INVALID_API_TOKEN")):
    """This is just an endpoing for enabling or disabling maintenance mode. As of the new API Revamp, this isi the only way to add a maint

    **API Token**: You can get this by clicking your bot and clicking edit and scrolling down to API Token

    **Mode**: Whether you want to enter or exit maintenance mode. Setting this to 1 will enable maintenance and setting this to 0 will disable maintenance mode. Different maintenance modes are planned
    """
    
    if api.mode not in [0, 1]:
        return {"done":  False, "reason": "UNSUPPORTED_MODE"}

    id = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(Authorization))
    if id is None:
        return {"done":  False, "reason": "NO_AUTH"}
    await add_maint(id["bot_id"], api.mode, api.reason)
    return {"done": True, "reason": None}

@router.get("/features/{name}", tags = ["API"])
async def get_feature_api(request: Request, name: str):
    """Gets a feature given its internal name (custom_prefix, open_source etc)"""
    if name not in features.keys():
        return abort(404)
    return features[name]


async def ws_send_events(websocket):
    for event_i in range(0, len(ws_events)):
        event = ws_events[event_i]
        for ws in manager.active_connections:
            if int(event[0]) in [int(bot_id["bot_id"]) for bot_id in ws.bot_id]:
                rc = await manager.send_personal_message({"msg": "EVENT", "data": event[1], "reason": event[0]}, ws)
                try:
                    if rc != False:
                        ws_events[event_i] = [-1, -2]
                except:
                    pass

async def recv_ws(websocket):
    print("Getting things")
    while True:
        if websocket not in manager.active_connections:
            print("Not connected to websocket")
            return
        print("Waiting for websocket")
        try:
            data = await websocket.receive_json()
            await manager.send_personal_message(data, websocket)
        except WebSocketDisconnect:
            print("Disconnect")
            return
        except:
            continue
        print(data)

@router.websocket("/api/ws")
async def websocker_real_time_api(websocket: WebSocket):
    await manager.connect(websocket)
    if websocket.api_token == []:
        await manager.send_personal_message({"msg": "IDENTITY", "reason": None}, websocket)
        try:
            api_token = await websocket.receive_json()
        except:
            await manager.send_personal_message({"msg": "KILL_CONN", "reason": "NO_AUTH"}, websocket)
            try:
                return await websocket.close(code=4004)
            except:
                return
        api_token = api_token.get("api_token")
        if api_token is None or type(api_token) == int:
            await manager.send_personal_message({"msg": "KILL_CONN", "reason": "NO_AUTH"}, websocket)
            try:
                return await websocket.close(code=4004)
            except:
                return
        for bot in api_token:
            bid = await db.fetchrow("SELECT bot_id, servers FROM bots WHERE api_token = $1", str(bot))
            if bid is None:
                pass
            else:
                websocket.api_token.append(api_token)
                websocket.bot_id.append(bid)
        if websocket.api_token == [] or websocket.bot_id == []:
            await manager.send_personal_message({"msg": "KILL_CONN", "reason": "NO_AUTH"}, websocket)
            return await websocket.close(code=4004)
    await manager.send_personal_message({"msg": "READY", "reason": "AUTH_DONE"}, websocket)
    await ws_send_events(websocket)
    asyncio.create_task(recv_ws(websocket))
    try:
        while True:
            await ws_send_events(websocket)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)

