from modules.core.system import setup_db, setup_discord
from fastapi import FastAPI
from lynxfall.utils.fastapi import include_routers
from .ipc import run_ipc

app = FastAPI(title="Management API")

@app.on_event("startup")
async def startup()
