import uvloop

uvloop.install()

from fastapi import FastAPI
from modules.core.system import init_fates_worker
from fastapi.responses import ORJSONResponse

# Setup FastAPI with required urls and orjson for faster json handling
app = FastAPI(
    default_response_class = ORJSONResponse, 
    redoc_url = "/api/docs/redoc", 
    docs_url = "/api/docs/swagger", 
    openapi_url = "/api/docs/openapi"
)

@app.on_event("startup")
async def startup():
    await init_fates_worker(app)
