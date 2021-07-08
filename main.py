import uvloop

uvloop.install()

from fastapi import FastAPI, Request
from fastapi.exceptions import (
    HTTPException, RequestValidationError, ValidationError
)
from loguru import logger
from fastapi.responses import ORJSONResponse
from modules.core.system import init_fates_worker
from modules.core.error import WebError
from modules.core.routeware import routeware

# Setup FastAPI with required urls and orjson for faster json handling
app = FastAPI(
    default_response_class = ORJSONResponse, 
    redoc_url = "/api/docs/redoc", 
    docs_url = "/api/docs/swagger", 
    openapi_url = "/api/docs/openapi"
)

# Setup exception handling
@app.exception_handler(403)
@app.exception_handler(404)
@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
@app.exception_handler(500)
@app.exception_handler(HTTPException)
@app.exception_handler(Exception)
async def fl_exception_handler(request, exc, log = True):
    return await WebError.error_handler(request, exc, log = log)

@app.on_event("startup")
async def startup():
    await init_fates_worker(app)
