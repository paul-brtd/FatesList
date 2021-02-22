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
from modules.Oauth import Oauth
from fastapi.templating import Jinja2Templates
import discord
import asyncio
import time
import re
import orjson
from starlette_wtf import CSRFProtectMiddleware, csrf_protect,StarletteForm
import builtins
from typing import Optional, List, Union
from aiohttp_requests import requests
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
from modules.emd_hab import emd
from config import *
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)

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

async def _internal_user_fetch(userid: str, bot_only: bool) -> Optional[dict]:
    # Check if a suitable version is in the cache first before querying Discord

    if len(userid) not in [17, 18]:
        print("Ignoring blatantly wrong User ID")
        return None # This is impossible to actually exist on the discord API or on our cache

    # Query redis cache for some important info
    cache_redis = await redis_db.hgetall(f"{userid}_cache", encoding = 'utf-8')
    if cache_redis is not None and cache_redis.get("cache_obj") is not None:
        cache = orjson.loads(cache_redis["cache_obj"])
        if cache.get("valid_user") is None or time.time() - cache['epoch'] > 60*60*8: # 8 Hour cacher
            # The cache is invalid, pass
            print("Not using cache for id ", userid)
            pass
        else:
            print("Using cache for id ", userid)
            if cache.get("valid_user") and bot_only and cache["bot"]:
                return {"username": cache['username'], "avatar": cache['avatar'], "disc": cache["disc"]}
            elif cache.get("valid_user") and not bot_only:
                return {"username": cache['username'], "avatar": cache['avatar'], "disc": cache["disc"]}
            return None

    # Add ourselves to cache
    valid_user = False
    bot = False
    username, avatar, disc = None, None, None # All are none at first

    try:
        print(f"Making API call to get user {userid}")
        bot_obj = await client.fetch_user(int(userid))
        valid_user = True
        bot = bot_obj.bot
    except:
        pass
    
    if valid_user:
        username = bot_obj.name
        avatar = str(bot_obj.avatar_url)
        disc = bot_obj.discriminator
    cache = orjson.dumps({"epoch": time.time(), "bot": bot, "username": username, "avatar": avatar, "disc": disc, "valid_user": valid_user})
    await redis_db.hset(f"{userid}_cache", mapping = {"cache_obj": cache})

    if bot_only and valid_user and bot:
        return {"username": username, "avatar": avatar, "disc": disc}
    elif not bot_only and valid_user and not bot:
        return {"username": username, "avatar": avatar, "disc": disc}
    return None

async def get_user(userid: int) -> Optional[dict]:
    return await _internal_user_fetch(str(int(userid)), False)

async def get_bot(userid: int) -> Optional[dict]:
    return await _internal_user_fetch(str(int(userid)), True)

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

async def set_stats(*, bot_id: int, guild_count: int, shard_count: int, user_count: int, shards: int):
    if int(guild_count) > 300000000000 or int(shard_count) > 300000000000:
        return
    await db.execute("UPDATE bots SET servers = $1, shard_count = $2, user_count = $3, shards = $4 WHERE bot_id = $5", guild_count, shard_count, user_count, shards, bot_id)

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
            json = json | {"payload": "event", "mode": webh["webhook_type"].upper()}
            try:
                del json["type"]
            except:
                pass
            asyncio.create_task(f(uri, json = json, headers = headers))
    await add_ws_event(bot_id, {"payload": "event", "id": str(id), "event": event, "context": context})
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

async def is_bot_admin(bot_id: int, user_id: int):
    guild = client.get_guild(reviewing_server)
    check = await db.fetchrow("SELECT owner, extra_owners FROM bots WHERE bot_id = $1", bot_id)
    if not check:
        return None
    user = guild.get_member(user_id)
    if check["extra_owners"] is None:
        eo = []
    else:
        eo = check["extra_owners"]
    if check["owner"] == user_id or user_id in eo or (user is not None and is_staff(staff_roles, user.roles, 4)[0]):
        return True
    else:
        return False

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

#CREATE TABLE bot_stats_votes (
#   bot_id bigint,
#   total_votes bigint
#);

#CREATE TABLE bot_stats_votes_pm (
#   bot_id bigint,
#   epoch bigint,
#   votes bigint
#);

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
    b = await db.fetchrow("SELECT webhook, votes FROM bots WHERE bot_id = $1", int(bot_id))
    voters = await db.fetchrow("SELECT timestamps FROM bots_voters WHERE bot_id = $1 AND userid = $2", int(bot_id), int(uid))
    if b is None:
        return [404]
    if voters is None:
        await db.execute("INSERT INTO bots_voters (userid, bot_id, timestamps) VALUES ($1, $2, $3)", int(uid), int(bot_id), [int(time.time())])
    else:
        voters["timestamps"].append(int(time.time()))
        ts = voters["timestamps"]
        await db.execute("UPDATE bots_voters SET timestamps = $1 WHERE bot_id = $2 AND userid = $3", ts, int(bot_id), int(uid))
    await db.execute("UPDATE bots SET votes = votes + 1 WHERE bot_id = $1", int(bot_id))
    await db.execute("UPDATE users SET vote_epoch = $1 WHERE userid = $2", time.time(), int(uid))

    # Update bot_stats
    check = await db.fetchrow("SELECT bot_id FROM bot_stats_votes WHERE bot_id = $1", int(bot_id))
    if check is None:
        await db.execute("INSERT INTO bot_stats_votes (bot_id, total_votes) VALUES ($1, $2)", int(bot_id), b["votes"] + 1)
    else:
        await db.execute("UPDATE bot_stats_votes SET total_votes = total_votes + 1 WHERE bot_id = $1", int(bot_id))

    event_id = asyncio.create_task(add_event(bot_id, "vote", {"username": username, "user_id": str(uid), "votes": b['votes'] + 1, "**Vote Here**": "https://fateslist.xyz/bot/" + str(bot_id)}))
    return []

async def parse_reviews(bot_id: int, reviews: List[asyncpg.Record] = None) -> List[dict]:
    if reviews is None:
        _rev = True
        reviews = await db.fetch("SELECT id, user_id, star_rating, review_text AS review, review_upvotes, review_downvotes, flagged, epoch, replies AS _replies FROM bot_reviews WHERE bot_id = $1 ORDER BY star_rating ASC", bot_id)
    else:
        _rev = False
    i = 0
    stars = 0
    while i < len(reviews):
        reviews[i] = dict(reviews[i])
        if reviews[i]["epoch"] in ([], None):
            reviews[i]["epoch"] = [time.time()]
        else:
            reviews[i]["epoch"].sort(reverse = True)
        reviews[i]["time_past"] = time.time() - reviews[i]["epoch"][0]
        reviews[i]["id"] = str(reviews[i]["id"])
        reviews[i]["user"] = await get_user(reviews[i]["user_id"])
        reviews[i]["star_rating"] = round(reviews[i]["star_rating"], 2)
        reviews[i]["replies"] = []
        if _rev:
            stars += reviews[i]["star_rating"]
        for review_id in reviews[i]["_replies"]:
            _reply = await db.fetch("SELECT id, user_id, star_rating, review_text AS review, review_upvotes, review_downvotes, flagged, epoch, replies AS _replies FROM bot_reviews WHERE id = $1", review_id)
            _parsed_reply = await parse_reviews(bot_id, _reply)
            reviews[i]["replies"].append(_parsed_reply)
        i+=1
    if i == 0:
        return reviews, 10.0
    return reviews, round(stars/i, 2)

# Get Bots Helper
async def render_bot(request: Request, bt: BackgroundTasks, bot_id: int, review: bool, widget: bool):
    guild = client.get_guild(reviewing_server)
    print("Begin rendering bots")
    bot = dict(await db.fetchrow("SELECT api_token, prefix, shard_count, queue, description, bot_library AS library, tags, banner, website, certified, votes, servers, bot_id, discord, owner, extra_owners, banner, banned, disabled, github, features, invite_amount, css, html_long_description AS html_ld, long_description FROM bots WHERE bot_id = $1", bot_id))
    print("Got here")
    if bot is None:
        return templates.e(request, "Bot Not Found")
    if not bot["html_ld"]:
        ldesc = emd(markdown.markdown(bot['long_description'], extensions=["extra", "abbr", "attr_list", "def_list", "fenced_code", "footnotes", "tables", "admonition", "codehilite", "meta", "nl2br", "sane_lists", "toc", "wikilinks", "smarty", "md_in_html"]))
    else:
        ldesc = bot['long_description']
    
    # Take the h1...h5 anad drop it one lower
    ldesc = ldesc.replace("<h1", "<h2 style='text-align: center'").replace("<h2", "<h3").replace("<h4", "<h5").replace("<h6", "<p")

    if widget:
        eo = []
        bot_admin = False
    else:
        if bot["extra_owners"] is None:
            eo = []
        else:
            eo = bot["extra_owners"]
        if "userid" in request.session.keys():
            bot_admin = await is_bot_admin(int(bot_id), int(request.session.get("userid"))) 
        else:
            bot_admin = False
    if not bot_admin:
        bot["api_token"] = None
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
        bot = bot | {"votes": human_format(bot["votes"]), "servers": human_format(bot["servers"]), "banner": banner.replace("\"", "").replace("'", "").replace("http://", "https://").replace("(", "").replace(")", "").replace("file://", ""), "shards": human_format(bot["shard_count"]), "owner_pretty": await get_user(bot["owner"]), "extra_owners": ed, "leo": len(ed), "features": features, "fleo": len(features), "long_description": ldesc.replace("window.location", "").replace("document.ge", ""), "user": (await get_bot(bot_id))}
    else:
        return templates.e(request, "Bot Not Found")
    _tags_fixed_bot = {tag: tags_fixed[tag] for tag in tags_fixed if tag in bot["tags"]}
    form = await Form.from_formdata(request)
    bt.add_task(add_ws_event, bot_id, {"payload": "event", "id": str(uuid.uuid4()), "event": "view", "context": {"user": 0, "hidden": 1, "widget": str(widget)}})
    if widget:
        f = "widget.html"
        reviews = [0, 1]
    else:
        f = "bot.html"
        reviews = await parse_reviews(bot_id)
    return templates.TemplateResponse(f, {"request": request, "bot": bot, "bot_id": bot_id, "tags_fixed": _tags_fixed_bot, "form": form, "avatar": request.session.get("avatar"), "promos": promos, "maint": maint, "bot_admin": bot_admin, "review": review, "guild": reviewing_server, "botp": True, "bot_reviews": reviews[0], "average_rating": reviews[1]})

#    id uuid primary key DEFAULT uuid_generate_v4(),
#   bot_id bigint not null,
#   star_rating float4 default 0.0,
#   review_text text,
#   review_upvotes integer default 0,
#   review_downvotes integer default 0,
#   flagged boolean default false,
#   epoch bigint

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
            banner = bot["banner"]
            del bot["banner"]
            lst.append({"avatar": bot_info["avatar"].replace("?size=1024", "?size=128"), "username": bot_info["username"], "votes": human_format(votes), "servers": human_format(servers), "description": bot["description"], "banner": banner.replace("\"", "").replace("'", "").replace("http://", "https://").replace("(", "").replace(")", "").replace("file://", "")} | bot)
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

# Check vanity of bot 
async def vanity_bot(vanity: str, compact = False):
    t = await db.fetchrow("SELECT type, redirect FROM vanity WHERE lower(vanity_url) = $1", vanity.lower())
    if t is None:
        return None
    if t["type"] == 1:
        type = "bot"
    else:
        type = "profile"
    if compact:
        return type, str(t["redirect"])
    return "/" + type + "/" + str(t["redirect"]), type

# WebSocket Base Code

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.fl_loaded = False
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


class templates():
    @staticmethod
    def TemplateResponse(f, arg_dict):
        guild = client.get_guild(reviewing_server)
        try:
            request = arg_dict["request"]
        except:
            raise KeyError
        status = arg_dict.get("status_code")
        if "userid" in request.session.keys():
            arg_dict["css"] = request.session.get("user_css")
            if "staff" not in arg_dict.keys():
                user = guild.get_member(int(request.session["userid"]))
                if user is not None:
                    staff = is_staff(staff_roles, user.roles, 2)
                else:
                    staff = [False]
                arg_dict["avatar"] = request.session.get("avatar")
                arg_dict["username"] = request.session.get("username")
                arg_dict["userid"] = int(request.session.get("userid"))
        else:
            staff = [False]
        arg_dict["staff"] = staff
        arg_dict["site_url"] = site_url
        if status is None:
            return _templates.TemplateResponse(f, arg_dict)
        return _templates.TemplateResponse(f, arg_dict, status_code = status)

    @staticmethod
    def error(f, arg_dict, status_code):
        arg_dict["status_code"] = status_code
        return templates.TemplateResponse(f, arg_dict)

    @staticmethod
    def e(request, reason: str, status_code: str = 404):
        return templates.error("message.html", {"request": request, "context": reason}, status_code)

def url_startswith(url, begin, slash = True):
    # Slash indicates whether to check /route or /route/
    if slash:
       begin = begin + "/"
    return str(url).startswith(site_url + begin)

_templates = Jinja2Templates(directory="templates")

class FLError():
    @staticmethod
    async def error_handler(request, exc):
        print(request.url)
        if type(exc) == RequestValidationError:
            exc.status_code = 422
        if exc.status_code == 404:
            if url_startswith(request.url, "/bot"):
                msg = "Bot Not Found"
                code = 404
            elif url_startswith(request.url, "/profile"):
                msg = "Profile Not Found"
                code = 404
            else:
                msg = "404\nNot Found"
                code = 404
        elif exc.status_code == 401:
            msg = "401\nNot Authorized"
            code = 401
        elif exc.status_code == 422:
            if url_startswith(request.url, "/bot"):
                msg = "Bot Not Found"
                code = 404
            elif url_startswith(request.url, "/profile"):
                msg = "Profile Not Found"
                code = 404
            else:
                msg = "Invalid Data Provided<br/>" + str(exc)
                code = 422

        json = url_startswith(request.url, "/api")
        if json:
            if exc.status_code != 422:
                return await http_exception_handler(request, exc)
            else:
                return await request_validation_exception_handler(request, exc)
        return templates.e(request, msg, code)

async def add_ws_event(bot_id: int, ws_event: dict) -> None:
    """A WS Event must have the following format:
        - {id: Event ID, event: Event Name, context: Context, type: Event Type}
    """
    curr_ws_events = await redis_db.hgetall(str(bot_id) + "_ws", encoding = 'utf-8')
    if curr_ws_events is None:
        curr_ws_events = {}
    curr_ws_events[ws_event["id"]] = orjson.dumps(ws_event)
    curr_ws_events["status"] = "READY"
    await redis_db.hset(str(bot_id) + "_ws", mapping = curr_ws_events)
