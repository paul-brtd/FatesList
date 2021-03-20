# Put all needed imports here
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
import socket
import contextvars
from starlette.websockets import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from aioredis.exceptions import ConnectionError as ServerConnectionClosedError
from discord_webhook import DiscordWebhook, DiscordEmbed
import markdown
from modules.emd_hab import emd
from config import *
from modules.utils import *
from fastapi.exceptions import RequestValidationError, ValidationError
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi_limiter.depends import RateLimiter
import lxml
from lxml.html.clean import Cleaner
import io
