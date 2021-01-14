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
    # Check if a suitable version is in the bot_cache first before querying Discord
    cache = await db.fetchrow("SELECT username, avatar, valid, valid_for, epoch FROM bot_cache WHERE bot_id = $1", userid)
    if cache is None or time.time() - cache['epoch'] > 300: # 300 sec cacher
        # The cache is invalid, pass
        pass
    else:
        if cache["valid"] and "bot" in cache["valid_for"].split("|"):
            return {"username": str(cache['username']), "avatar": str(cache['avatar'])}
        elif cache["valid"] and not bot_only:
            return {"username": str(cache['username']), "avatar": str(cache['avatar'])}
        return None

    # If all else fails, add to cache, then recall ourselves
    invalid = False
    
    try:
        bot = client.get_user(int(userid))
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
 
    cache = await db.fetchrow("SELECT epoch FROM bot_cache WHERE bot_id = $1", userid)
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

class Form(StarletteForm):
    pass
