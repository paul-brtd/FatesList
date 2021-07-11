import uvloop

uvloop.install()

from fastapi import FastAPI
from modules.core.system import init_fates_worker
from fastapi.responses import ORJSONResponse
from config import API_VERSION

# Setup FastAPI with required urls and orjson for faster json handling
app = FastAPI(
    default_response_class = ORJSONResponse, 
    redoc_url = f"/api/v{API_VERSION}/docs/redoc", 
    docs_url = f"/api/v{API_VERSION}/docs/swagger", 
    openapi_url = f"/api/v{API_VERSION}/docs/openapi"
)

@app.on_event("startup")
async def startup():
    await init_fates_worker(app)
