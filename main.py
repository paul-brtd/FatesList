from fastapi import FastAPI, Request,Form
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import Oauth
import aiohttp
import asyncpg
import json
import os
import datetime
import random, math, time
import uuid
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from pydantic import BaseModel
from starlette.status import HTTP_302_FOUND,HTTP_303_SEE_OTHER
import secrets,string


app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="E@Dycude3u8z382")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_token(length: str) -> str:
    secure_str = "".join(
        (secrets.choice(string.ascii_letters + string.digits) for i in range(length))
    )
    return secure_str
templates = Jinja2Templates(directory="templates")

async def setup_db():

    db = asyncpg.create_pool(host="107.152.38.124", port = "5432", username = "postgres", password = "rocco123", database = "a dB u create in pgadmin")

    # some table creation here meow

    return db
@app.on_event("startup")
async def startup():
    global db
    dB = await setup_db()


@app.get("/")
async def home(request:Request):
    return templates.TemplateResponse("index.html", {"request":request})
