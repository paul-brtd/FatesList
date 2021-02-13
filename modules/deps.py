import string
import secrets
from fastapi import Request, APIRouter, BackgroundTasks, Form as FForm, Header, WebSocket, WebSocketDisconnect, File, UploadFile, Depends
import aiohttp
import asyncpg
import datetime
import random
import math
import time
import uuid
from fastapi.responses import HTMLResponse, RedirectResponse, ORJSONResponse
from pydantic import BaseModel
from starlette.status import HTTP_302_FOUND, HTTP_303_SEE_OTHER
import secrets
import string
import discord
import asyncio
import time
import re
import orjson
from starlette_wtf import CSRFProtectMiddleware, csrf_protect,StarletteForm
import builtins
from typing import Optional, List, Union
from aiohttp_requests import requests as _r_
from starlette.exceptions import HTTPException as StarletteHTTPException
from websockets.exceptions import ConnectionClosedOK
import hashlib
import aioredis
import uvloop
import socket
import uuid
import contextvars
from fastapi import FastAPI, Depends, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from aioredis.errors import ConnectionClosedError as ServerConnectionClosedError
from discord_webhook import DiscordWebhook, DiscordEmbed
import markdown
class requests:
    @staticmethod
    async def put(url, json = None, headers = None):
        a = await _r_.put(url, json = json, headers = headers)
        print(a, "\n")
    @staticmethod
    async def post(url, json = None, headers = None):
        a = await _r_.post(url, json = json, headers = headers)
        print(a, "\n")
    @staticmethod
    async def get(url, headers = None):
        a = await _r_.get(url, headers = headers)
        print(a, "\n")

def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=HTTP_303_SEE_OTHER)


def abort(code: str) -> StarletteHTTPException:
    raise StarletteHTTPException(status_code=code)


# Secret creator


def get_token(length: str) -> str:
    secure_str = "".join(
        (secrets.choice(string.ascii_letters + string.digits)
         for i in range(length))
    )
    return secure_str

def human_format(num: int) -> str:
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        if magnitude == 31:
            num /= 10
        num /= 1000.0
    return '{} {}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T', "Quad.", "Quint.", "Sext.", "Sept.", "Oct.", "Non.", "Dec.", "Tre.", "Quat.", "quindec.", "Sexdec.", "Octodec.", "Novemdec.", "Vigint.", "Duovig.", "Trevig.", "Quattuorvig.", "Quinvig.", "Sexvig.", "Septenvig.", "Octovig.", "Nonvig.", "Trigin.", "Untrig.", "Duotrig.", "Googol."][magnitude])

async def internal_get_bot(userid: int, bot_only: bool) -> Optional[dict]:
    userid = int(userid)
    # Check if a suitable version is in the bot_cache first before querying Discord

    if len(str(userid)) not in [17, 18]:
        print("Ignoring blatantly wrong User ID")
        return None # This is impossible to actually exist on the discord API

    cache = await db.fetchrow("SELECT username, avatar, valid, valid_for, epoch FROM bot_cache WHERE bot_id = $1 AND username IS NOT NULL AND avatar IS NOT NULL", int(userid))
    if cache is None or time.time() - cache['epoch'] > 60 * 60 * 4: # 4 Hour cacher
        # The cache is invalid, pass
        print("Not using cache for id ", str(userid))
        pass
    else:
        print("Using cache for id ", str(userid))
        if cache["valid"] and "bot" in cache["valid_for"].split("|"):
            return {"username": str(cache['username']), "avatar": str(cache['avatar'])}
        elif cache["valid"] and not bot_only:
            return {"username": str(cache['username']), "avatar": str(cache['avatar'])}
        return None

    # If all else fails, add to cache, then recall ourselves
    invalid = False
    
    try:
        print("Making API call to get user", str(userid))
        bot = await client.fetch_user(int(userid))
    except:
        invalid = True
        valid_for = None
        return None

    if bot:
        invalid = False
        valid_for = "user"
    else:
        invalid = True
        valid_for = None

    if bot and bot.bot:
        invalid = False
        valid_for+="|bot"

    if invalid:
        username = None
        avatar = None
    else:
        username = str(bot.name)
        avatar = str(bot.avatar_url)
 
    cache = await db.fetchrow("SELECT epoch FROM bot_cache WHERE bot_id = $1", int(userid))
    if cache is None:
        await db.execute("INSERT INTO bot_cache (bot_id, username, avatar, epoch, valid, valid_for) VALUES ($1, $2, $3, $4, $5, $6)", userid, username, avatar, time.time(), (not invalid), valid_for)
    else:
        await db.execute("UPDATE bot_cache SET username = $1, avatar = $2, epoch = $3, valid = $4, valid_for = $6 WHERE bot_id = $5", username, avatar, time.time(), (not invalid), userid, valid_for)
    return await internal_get_bot(userid, bot_only)

async def get_user(userid: int) -> Optional[dict]:
    return await internal_get_bot(userid, False)

async def get_bot(userid: int) -> Optional[dict]:
    return await internal_get_bot(userid, True)

# Internal backend entry to check if one role is in staff and return a dict of that entry if so
def is_staff_internal(staff_json: dict, role: int) -> dict:
    for key in staff_json.keys():
        if int(role) == int(staff_json[key]["id"]):
            return staff_json[key]
    return None

def is_staff(staff_json: dict, roles: Union[list, int], base_perm: int) -> Union[bool, Optional[int]]:
    if type(roles) == list:
        max_perm = 0 # This is a cache of the max perm a user has
        for role in roles:
            if type(role) == discord.Role:
                role = role.id
            tmp = is_staff_internal(staff_json, role)
            if tmp is not None and tmp["perm"] > max_perm:
                max_perm = tmp["perm"]
        if max_perm >= base_perm:
            return True, max_perm
        return False, max_perm
    else:
        tmp = is_staff_internal(staff_json, roles)
        if tmp is not None and tmp["perm"] >= base_perm:
            return True, tmp["perm"]
        return False, tmp["perm"]
    return False, tmp["perm"]

async def add_maint(bot_id: int, type: int, reason: str):
    return await db.execute("INSERT INTO bot_maint (bot_id, reason, type, epoch) VALUES ($1, $2, $3, $4)", bot_id, reason, type, time.time())

async def set_stats(*, bot_id: int, guild_count: int, shard_count: int, user_count: Optional[int] = None):
    if int(guild_count) > 300000000000 or int(shard_count) > 300000000000:
        return
    await db.execute("UPDATE bots SET servers = $1, shard_count = $2 WHERE bot_id = $3", guild_count, shard_count, bot_id)
    if user_count is not None:
        await db.execute("UPDATE bots SET user_count = $1 WHERE bot_id = $2", user_count, bot_id)

async def add_promotion(bot_id: int, title: str, info: str, css: str):
    if css is not None:
        css = css.replace("</style", "").replace("<script", "")
    info = info.replace("</style", "").replace("<script", "")
    return await db.execute("INSERT INTO promotions (bot_id, title, info, css) VALUES ($1, $2, $3, $4)", bot_id, title, info, css)

async def add_event(bot_id: int, event: str, context: dict, *, send_event = True):
    if type(context) == dict:
        pass
    else:
        raise KeyError

    new_event_data = [event, str(time.time()), orjson.dumps(context).decode()]
    id = uuid.uuid4()
    apitok = await db.fetchrow("SELECT api_token FROM bots WHERE bot_id = $1", bot_id)
    if apitok is None:
        return
    asyncio.create_task(db.execute("INSERT INTO api_event (id, bot_id, events) VALUES ($1, $2, $3)", id, bot_id, new_event_data))
    webh = await db.fetchrow("SELECT webhook, webhook_type FROM bots WHERE bot_id = $1", int(bot_id))
    if webh is not None and webh["webhook"] not in ["", None] and webh["webhook_type"] is not None and send_event:
        uri = webh["webhook"]
        cont = True
        if webh["webhook_type"].upper() == "FC":
            f = requests.put
            print("Doing FC\n\n\n")
        elif webh["webhook_type"].upper() == "DISCORD" and event in ["edit_bot", "vote"]:
            print("Doing DISCORD")
            webhook = DiscordWebhook(url=uri)
            print(context)
            embed = DiscordEmbed(
                title=event.replace("_", " ").title(),
                description="\n".join([f"{key.replace('_', ' ').title()}: {value}" for key, value in context.items() if key != "user_id"]),
                color=242424
            )
            print(embed.description)
            webhook.add_embed(embed)
            response = webhook.execute()
            cont = False
        elif webh["webhook_type"].upper() == "VOTE" and event == "vote":
            print("Doing VOTE")
            f = requests.post
            json = {"id": str(context["user_id"]), "votes": context["votes"]}
            headers = {"Authorization": apitok["api_token"]}
            print("Ready")
        else:
            print("Invalid method given\n\n\n")
            cont = False
        if cont:
            print(f"JSON: {json}\nFunction: {f}\nURL: {uri}\nHeaders: {headers}")
            json = json | {"mode": webh["webhook_type"].upper()}
            asyncio.create_task(f(uri, json = json, headers = headers))
    ws_events.append((bot_id, {"type": "add", "event_id": str(id), "event": event, "context": context}))
    return id

class Form(StarletteForm):
    pass

async def in_maint(bot_id: str) -> Union[bool, Optional[dict]]:
    api_data = await db.fetch("SELECT type, reason, epoch FROM bot_maint WHERE bot_id = $1", bot_id)
    if api_data == []:
        return False, None
    curr_maint = None
    for _maint in api_data:
        if _maint["type"] != 0:
            curr_maint = _maint
        elif _maint["type"] == 0 and curr_maint is not None:
            curr_maint = None
    if curr_maint is not None:
        return True, {"reason": curr_maint["reason"], "epoch": curr_maint["epoch"]}
    else:
        return False, None

async def get_promotions(bot_id: int) -> list:
    api_data = await db.fetch("SELECT title, info, css FROM promotions WHERE bot_id = $1", bot_id)
    return api_data

async def get_user_token(uid: int, username: str) -> str:
        token = await db.fetchrow("SELECT username, token FROM users WHERE userid = $1", int(uid))
        if token is None:
            flag = True
            while flag:
                token = get_token(101)
                tcheck = await db.fetchrow("SELECT token FROM users WHERE token = $1", token)
                if tcheck is None:
                    flag = False
            await db.execute("INSERT INTO users (userid, token, vote_epoch, username) VALUES ($1, $2, $3, $4)", int(uid), token, 0, username)
        else:
            # Update their username if needed
            if token["username"] != username:
                print("Updating profile")
                await db.execute("UPDATE users SET username = $1 WHERE userid = $2", username, int(uid))
            token = token["token"]

async def vote_bot(uid: int, bot_id: int, username, autovote: bool) -> Optional[list]:
    await get_user_token(uid, username) # Make sure we have a user profile first
    epoch = await db.fetchrow("SELECT vote_epoch FROM users WHERE userid = $1", int(uid))
    if epoch is None:
        return [500]
    epoch = epoch["vote_epoch"]
    if autovote:
        WT = 60*60*11 # Autovote Wait Time
    else:
        WT = 60*60*8 # Wait Time
    if time.time() - epoch < WT:
        return [401, str(WT - (time.time() - epoch))]
    b = await db.fetchrow("SELECT webhook, votes, voters FROM bots WHERE bot_id = $1", int(bot_id))
    if b is None:
        return [404]
    if b["voters"] is None:
        voters = [int(uid)]
    else:
        voters = b["voters"]
        voters.append(int(uid))
    await db.execute("UPDATE bots SET votes = votes + 1, voters = $2 WHERE bot_id = $1", int(bot_id), voters)
    await db.execute("UPDATE users SET vote_epoch = $1 WHERE userid = $2", time.time(), int(uid))
    event_id = asyncio.create_task(add_event(bot_id, "vote", {"username": username, "user_id": str(uid), "votes": b['votes'] + 1, "**Vote Here**": "https://fateslist.xyz/bot/" + str(bot_id)}))
    return []

# Get Bots Helper
async def render_bot(request: Request, bot_id: int, review: bool, widget: bool):
    guild = client.get_guild(reviewing_server)
    print("Begin rendering bots")
    bot = await db.fetchrow("SELECT prefix, shard_count, queue, description, bot_library AS library, tags, banner, website, certified, votes, servers, bot_id, discord, owner, extra_owners, banner, banned, disabled, github, features, invite_amount, css, html_long_description AS html_ld, long_description FROM bots WHERE bot_id = $1", bot_id)
    print("Got here")
    if bot is None:
        return templates.e(request, "Bot Not Found")
    if not bot["html_ld"]:
        ldesc = markdown.markdown(bot['long_description'])
    else:
        ldesc = bot['long_description']
    
    # Take the h1...h5 anad drop it one lower
    ldesc = ldesc.replace("h1", "h2").replace("h2", "h3").replace("h4", "h5").replace("h6", "p")

    if widget:
        eo = []
        bot_admin = False
        upubav = None
    else:
        if bot["extra_owners"] is None:
            eo = []
        else:
            eo = bot["extra_owners"]
        if "userid" in request.session.keys():
            user = guild.get_member(int(request.session.get("userid")))
            if (await redis_db.get(str(request.session.get("userid")) + str(bot_id))) is not None:
                upubav = await redis_db.get(str(request.session.get("userid")) + str(bot_id))
                upubav = upubav.decode()
            else:
                upubav = get_token(11).upper()
                await redis_db.set(str(request.session.get("userid")) + str(bot_id),  upubav)
            bot_admin = bot["owner"] == int(request.session["userid"]) or int(request.session["userid"]) in eo or (user is not None and is_staff(staff_roles, user.roles, 4)[0])
        else:
            bot_admin = False
            upubav = None
    img_header_list = ["image/gif", "image/png", "image/jpeg", "image/jpg"]
    banner = bot["banner"].replace(" ", "%20").replace("\n", "")
    try:
        res = await requests.get(banner)
        if response.headers['Content-Type'] not in header_list:
            banner = "none"
    except:
        banner = "none"
    bot_info = await get_bot(bot["bot_id"])
    promos = await get_promotions(bot["bot_id"])
    maint = await in_maint(bot["bot_id"])
    ed = [((await get_user(id)), id) for id in eo]
    if bot["features"] is None:
        features = []
    else:
        features = bot["features"]
    if bot_info:
        bot = dict(bot)
        bot_obj = {"bot_id": bot["bot_id"], "avatar": bot_info["avatar"], "website": bot["website"], "username": bot_info["username"], "votes": human_format(bot["votes"]), "servers": human_format(bot["servers"]), "description": bot["description"], "support": bot['discord'], "invite_amount": bot["invite_amount"], "tags": bot["tags"], "library": bot['library'], "banner": banner, "shards": human_format(bot["shard_count"]), "owner": bot["owner"], "owner_pretty": await get_user(bot["owner"]), "banned": bot['banned'], "disabled": bot['disabled'], "prefix": bot["prefix"], "github": bot['github'], "extra_owners": ed, "leo": len(ed), "queue": bot["queue"], "features": features, "fleo": len(features), "css": bot["css"], "long_description": ldesc}
    else:
        return templates.e(request, "Bot Not Found")
    _tags_fixed_bot = {tag: tags_fixed[tag] for tag in tags_fixed if tag in bot["tags"]}
    form = await Form.from_formdata(request)
    ws_events.append((bot_id, {"type": "view", "event_id": None, "event": "view", "context": "user=0::hidden=1:widget=" + str(widget)}))
    if widget:
        f = "widget.html"
        widget = True
    else:
        f = "bot.html"
        widget = False
    return templates.TemplateResponse(f, {"request": request, "bot_id": bot_id, "bot": bot_obj, "tags_fixed": _tags_fixed_bot, "form": form, "avatar": request.session.get("avatar"), "promos": promos, "maint": maint, "bot_admin": bot_admin, "review": review, "guild": reviewing_server, "widget": widget, "pubav": upubav})

async def parse_bot_list(fetch: List[asyncpg.Record]) -> list:
    lst = []
    for bot in fetch:
        bot_info = await get_bot(bot["bot_id"])
        if bot_info:
            bot = dict(bot)
            votes = bot["votes"]
            servers = bot["servers"]
            del bot["votes"]
            del bot["servers"]
            lst.append({"avatar": bot_info["avatar"], "username": bot_info["username"], "votes": human_format(votes), "servers": human_format(servers), "description": bot["description"]} | bot)
    return lst

async def do_index_query(add_query: str) -> List[asyncpg.Record]:
    base_query = "SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false AND banned = false AND disabled = false"
    end_query = "DESC LIMIT 12"
    return await db.fetch(" ".join((base_query, add_query, end_query)))

async def render_index(request: Request, api: bool):
    top_voted = await parse_bot_list((await do_index_query("ORDER BY votes")))
    new_bots = await parse_bot_list((await do_index_query("ORDER BY created_at"))) # and certified = true ORDER BY votes
    certified_bots = await parse_bot_list((await do_index_query("and certified = true ORDER BY votes")))
    base_json = {"tags_fixed": tags_fixed, "top_voted": top_voted, "new_bots": new_bots, "certified_bots": certified_bots, "roll_api": "/api/bots/random"}
    if not api:
        return templates.TemplateResponse("index.html", {"request": request} | base_json)
    else:
        return base_json

async def render_search(request: Request, q: str, api: bool):
    if q == "":
        if api:
            return abort(404)
        else:
            return RedirectResponse("/")
    try:
        es = " OR owner = " + str(int(q)) + f" OR {str(q)} = ANY(extra_owners) OR bot_id = " + str(int(q))
    except:
        es = ""
    desc = ("SELECT bot_id FROM bots WHERE (queue = false and banned = false and disabled = false) and (description ilike '%" + re.sub(r'\W+|_', ' ', q) + "%'" + es + ")")
    print(desc)
    desc = await db.fetch(desc)
    userc = await db.fetch("SELECT bot_id FROM bot_cache WHERE username ilike '%" + re.sub(r'\W+|_', ' ', q) + "%' and valid_for ilike '%bot%'")
    bids = list(set([id["bot_id"] for id in desc]).union(set([id["bot_id"] for id in userc])))
    print(bids, desc, userc)
    data = str(tuple([int(bid) for bid in bids])).replace("(", "").replace(")", "")
    print("data is " + data)
    if data.replace(" ", "") in ["()", None, ",", ""]:
        fetch = []
    elif data.split(",")[-1].replace(" ", "") == "":
        data = data.replace(",", "")
        fetch = None
    else:
        fetch = None
    if fetch is None:
        abc = ("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE queue = false and banned = false and disabled = false and bot_id IN (" + data + ") ORDER BY votes DESC LIMIT 12")
        fetch = await db.fetch(abc)
    search_bots = await parse_bot_list(fetch)
    if not api:
        return templates.TemplateResponse("search.html", {"request": request, "search_bots": search_bots, "tags_fixed": tags_fixed, "query": q, "profile_search": False})
    else:
        return {"search_bots": search_bots, "tags_fixed": tags_fixed, "query": q, "profile_search": False}
# WebSocket Base Code

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, api: bool = True):
        await websocket.accept()
        if api:
            try:
                print(websocket.api_token)
            except:
                websocket.api_token = []
                websocket.bot_id = []
        else:
            websocket.api_token = []
            websocket.bot_id = []
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        try:
            await websocket.close(code=4005)
        except:
            pass
        self.active_connections.remove(websocket)
        websocket.api_token = []
        websocket.bot_id = []
        print(self.active_connections)

    async def send_personal_message(self, message, websocket: WebSocket):
        i = 0
        if websocket not in self.active_connections:
            await manager.disconnect(websocket)
            return False
        while i < 6:
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

try:
    a = builtins.manager
except:
    builtins.manager = ConnectionManager()

async def get_events(api_token: Optional[str] = None, bot_id: Optional[str] = None, event_id: Optional[uuid.UUID] = None):
    if api_token is None and bot_id is None:
        return {"events": []}
    if api_token is None:
        bid = await db.fetchrow("SELECT bot_id, servers FROM bots WHERE bot_id = $1", bot_id)
    else:
        bid = await db.fetchrow("SELECT bot_id, servers FROM bots WHERE api_token = $1", api_token)
    if bid is None:
        return {"events": []}
    uid = bid["bot_id"]
    # As a replacement/addition to webhooks, we have API events as well to allow you to quickly get old and new events with their epoch
    if event_id is not None:
        api_data = await db.fetchrow("SELECT id, events FROM api_event WHERE bot_id = $1 AND id = $2", uid, event_id)
        if api_data is None:
            return {"events": []}
        event = api_data["events"]
        return {"events": [{"id": uid,  "event": event[0], "epoch": event[1], "context": event[2]}]}

    api_data = await db.fetch("SELECT id, events FROM api_event WHERE bot_id = $1 ORDER BY id", uid)
    if api_data == []:
        return {"events": []}
    events = []
    for _event in api_data:
        event = _event["events"]
        uid = _event["id"]
        events.append({"id": uid,  "event": event[0], "epoch": event[1], "context": orjson.loads(event[2])})
    ret = {"events": events}
    return ret
