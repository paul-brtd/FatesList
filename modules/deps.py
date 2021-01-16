import string
import secrets
from fastapi import Request, APIRouter, BackgroundTasks, Form as FForm
import aiohttp
import asyncpg
import json
import os
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
from starlette_wtf import CSRFProtectMiddleware, csrf_protect,StarletteForm
import builtins
from typing import Optional, List, Union
from aiohttp_requests import requests
from starlette.exceptions import HTTPException as StarletteHTTPException

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

async def human_format(num: int) -> str:
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T'][magnitude])

async def internal_get_bot(userid: int, bot_only: bool) -> Optional[dict]:
    userid = int(userid)
    # Check if a suitable version is in the bot_cache first before querying Discord

    if len(str(userid)) not in [17, 18]:
        print("Ignoring blatantly wrong User ID")
        return None # This is impossible to actually exist on the discord API

    cache = await db.fetchrow("SELECT username, avatar, valid, valid_for, epoch FROM bot_cache WHERE bot_id = $1 AND username IS NOT NULL AND avatar IS NOT NULL", int(userid))
    if cache is None or time.time() - cache['epoch'] > 60 * 60 * 2: # 300 sec cacher
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

#await add_event(bot_id, "add_bot", "NULL")
async def add_event(bot_id: int, event: str, context: str):
    # Special Events
    if event == "guild_count":
        await db.execute("UPDATE bots SET servers = $1 WHERE bot_id = $2", int(context), int(bot_id))
        return
    elif event == "shard_count":
        await db.execute("UPDATE bots SET shard_count = $1 WHERE bot_id = $2", int(context), int(bot_id))

    new_event_data = "|".join((event, str(time.time()), context))
    id = uuid.uuid4()
    await db.execute("INSERT INTO api_event (id, bot_id, events) VALUES ($1, $2, $3)", id, bot_id, new_event_data)
    webh = await db.fetchrow("SELECT webhook FROM bots WHERE bot_id = $1", int(bot_id))
    if webh is not None and webh["webhook"] not in ["", None] and webh["webhook"].startswith("http"):
        await requests.patch(webh["webhook"], json = {"event_id": str(id), "event": event, "context": context})
    return id

class Form(StarletteForm):
    pass

async def in_maint(bot_id: str) -> Union[bool, Optional[dict]]:
    api_data = await db.fetch("SELECT events FROM api_event WHERE bot_id = $1 AND events ilike '%maint%'", bot_id)
    if api_data == []:
        return False, None
    curr_maint = None
    for _event in api_data:
        event = _event["events"]
        if event.split("|")[0].replace(" ", "") == "begin_maint":
            curr_maint = event
        elif event.split("|")[0].replace(" ", "") == "end_maint" and curr_maint is not None:
            curr_maint = None
    if curr_maint is not None:
        return True, {"reason": curr_maint.split("|")[2], "epoch": curr_maint.split("|")[1]}
    else:
        return False, None


# events = await get_normal_events(bot["bot_id"])
async def get_normal_events(bot_id: int) -> list:
    api_data = await db.fetch("SELECT events FROM api_event WHERE bot_id = $1", bot_id)
    if api_data == []:
        return []
    special_events = ["add_bot", "edit_bot", "guild_count", "shard_count", "begin_maint", "end_maint", "vote"]
    events = []
    for _event in api_data:
        event = _event["events"]
        if len(event.split("|")[0]) < 3:
            continue
        elif event.split("|")[0].replace(" ", "") in special_events:
            print("Ignoring event: ", event.split("|")[0].replace(" ", ""))
        else:
            try:
                css = event.split("|")[2].split("::css=")[1]
            except:
                css = ""
            events.append({"event": event.split("|")[0], "context": event.split("|")[2].split("::css=")[0].replace("onload", "").replace("<script", "").replace("</script>", "").replace("<iframe", ""), "css": css, "time": datetime.datetime.fromtimestamp(float(event.split("|")[1]))})
    print(events)
    return events

async def get_user_token(uid: int) -> str:
        token = await db.fetchrow("SELECT token FROM users WHERE userid = $1", int(uid))
        if token is None:
            flag = True
            while flag:
                token = get_token(101)
                tcheck = await db.fetchrow("SELECT token FROM users WHERE token = $1", token)
                if tcheck is None:
                    flag = False
            await db.execute("INSERT INTO users (userid, token, vote_epoch) VALUES ($1, $2, $3)", int(uid), token, 0)
        else:
            token = token["token"]

async def vote_bot(uid: int, bot_id: int) -> Optional[list]:
    await get_user_token(uid) # Make sure we have a user profile first
    epoch = await db.fetchrow("SELECT vote_epoch FROM users WHERE userid = $1", int(uid))
    if epoch is None:
        return [500]
    epoch = epoch["vote_epoch"]
    WT = 60*60*12 # Wait Time
    if time.time() - epoch < WT:
        return [401, str(WT - (time.time() - epoch))]
    b = await db.fetchrow("SELECT webhook, votes FROM bots WHERE bot_id = $1", int(bot_id))
    if b is None:
        return [404]
    await db.execute("UPDATE bots SET votes = votes + 1 WHERE bot_id = $1", int(bot_id))
    await db.execute("UPDATE users SET vote_epoch = $1 WHERE userid = $2", time.time(), int(uid))
    event_id = await add_event(bot_id, "vote", "user=" + str(uid) + "::votes=" + str(b['votes'] + 1))
    return []
