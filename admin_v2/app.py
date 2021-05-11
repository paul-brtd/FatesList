from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from piccolo_admin.endpoints import create_admin
from piccolo_api.crud.endpoints import PiccoloCRUD
from piccolo_api.fastapi.endpoints import FastAPIWrapper
from piccolo.engine import engine_finder
from tables import Vanity, User, Bot
from starlette.routing import Mount

admin = create_admin([Vanity, User, Bot], allowed_hosts = ["staff.fateslist.xyz"], production = True)
app = FastAPI(routes=[Mount("/", admin)])

@app.on_event("startup")
async def startup():
    engine = engine_finder()
    await engine.start_connection_pool()

@app.on_event("shutdown")
async def close():
    await engine.close_connection_pool()
