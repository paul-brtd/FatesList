# Put all needed imports here
import asyncio
import datetime
import inspect
import math
import random
import time
import traceback as tblib
import uuid
from copy import deepcopy
from http import HTTPStatus
from typing import List, Optional, Union

import aiohttp
import lxml
import markdown
import orjson
import discord
from aioredis.exceptions import ConnectionError as ServerConnectionClosedError
from fastapi import APIRouter, BackgroundTasks, Depends, File
from fastapi import Form as FForm
from fastapi import (Header, HTTPException, Query, Request, Response,
                     UploadFile, WebSocket, WebSocketDisconnect)
from fastapi.exception_handlers import (http_exception_handler,
                                        request_validation_exception_handler)
from fastapi.exceptions import (HTTPException, RequestValidationError,
                                ValidationError)
from fastapi.responses import HTMLResponse, ORJSONResponse, RedirectResponse
from pydantic import BaseModel
from starlette.datastructures import URL
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import ClientDisconnect
from starlette.routing import Mount
from starlette.websockets import WebSocket, WebSocketDisconnect
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

import modules.models.enums as enums
from config import *
from lynxfall.mdextend import *
from lynxfall.utils import *
from lynxfall.ratelimits.depends import Ratelimiter, Limit
from lynxfall.rabbit.client.core import *
