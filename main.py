import uvloop
uvloop.install()
from modules.core import *

builtins.boot_time = time.time()

sentry_sdk.init(sentry_dsn)

builtins.client, builtins.client_servers = setup_discord()

# Setup FastAPI with required urls and orjson for faster json handling
app = FastAPI(default_response_class = ORJSONResponse, redoc_url = "/api/docs/redoc", docs_url = "/api/docs/swagger", openapi_url = "/api/docs/openapi")

# Add Sentry
app.add_middleware(SentryAsgiMiddleware)

# Setup CSRF protection
class CsrfSettings(BaseModel):
    secret_key: str = csrf_secret

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()

builtins.CsrfProtect = CsrfProtect

# Setup exception handling
@app.exception_handler(401)
@app.exception_handler(403)
@app.exception_handler(404)
@app.exception_handler(RequestValidationError)
@app.exception_handler(ValidationError)
@app.exception_handler(500)
@app.exception_handler(HTTPException)
@app.exception_handler(Exception)
async def fl_exception_handler(request, exc, log = True):
    return await WebError.error_handler(request, exc, log = log)

logger.info("Loading modules for Fates List")

include_routers(app, "Discord", "modules/discord")

logger.info("All discord modules have loaded successfully!")

async def setup_db():
    """Function to setup the asyncpg connection pool"""
    db = await asyncpg.create_pool(host="localhost", port=12345, user=pg_user, database="fateslist")

    return db

@app.on_event("startup")
async def startup():
    await startup_tasks()

@app.on_event("shutdown")
async def close():
    """Close all connections on shutdown"""
    logger.info("Killing Fates List")
    await redis_db.publish("_worker", f"DOWN WORKER {os.getpid()}") # Announce that we are down
    await redis_db.close()
    await rabbitmq_db.close()
    await db.close()
    logger.info("Killed")

# Two events to let us know when discord.py is up and ready
@client.event
async def on_ready():
    logger.info(f"{client.user} up")

@client_servers.event
async def on_ready():
    logger.info(f"{client_servers.user} up")

# Two variables used in our logger
BOLD_START =  "\033[1m"
BOLD_END = "\033[0m"

@app.middleware("http")
async def fateslist_request_handler(request: Request, call_next):
    """
        Simple middleware to:
            - Handle API version and internally redirect by changing ASGI scope at request.scope
            - Transparently redirect /bots to /bot and /servers to /servers/index by changing ASGI scope (no 303 since thats bad UX)
            - Set and record the process time for analytics
    """
    request.scope["error_id"] = str(uuid.uuid4()) # Create a error id for just in case
    request.scope["curr_time"] = str(datetime.datetime.now()) # Get time request was made
    logger.trace(request.headers.get("X-Forwarded-For"))
    if str(request.url.path).startswith("/bots/"):
        request.scope["path"] = str(request.url.path).replace("/bots", "/bot", 1)
    request.scope, api_ver = version_scope(request, 2) # Transparently redirect /api to /api/vX excluding docs and already /api/vX'd apis
    start_time = time.time() # Get process time start
    try:
        response = await asyncio.shield(call_next(request)) # Process request
    except Exception as exc: # Try request again
        try:
            request._is_disconnected = False
        except:
            logger.warn("User {request.headers.get('X-Forwarded-For')} disconnected")
        try:
            response = await asyncio.shield(call_next(request))
        except Exception as exc:
            logger.exception("Site Error Occurred")
            response = await fl_exception_handler(request, exc)

    process_time = time.time() - start_time # Get time taken
    response.headers["X-Process-Time"] = str(process_time) # Record time taken
    response.headers["FL-API-Version"] = api_ver # Record currently used api version for debug
    # Fuck CORS
    response.headers["Access-Control-Allow-Origin"] = request.headers.get('Origin') if request.headers.get('Origin') else "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    asyncio.create_task(print_req(request, response))
    return response

async def print_req(request, response):
    # Gunicorn logging is trash, lets fix that with custom logging
    query_str = f'?{request.scope["query_string"].decode("utf-8")}' if request.scope["query_string"] else "" # Get query strings
    logger.info(f"{request.client.host}: {BOLD_START}{request.method} {request.url.path}{query_str} HTTP/{request.scope['http_version']} - {response.status_code} {HTTPStatus(response.status_code).phrase}{BOLD_END}") # Print logs like uvicorn

def fl_openapi():
    """Custom OpenAPI description"""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Fates List",
        version="1.0",
        description="Only v2 beta 2 API is supported (v1 is the old one that fateslist.js currently uses). The default API is v2. This means /api will point to this. To pin a api, either use the FL-API-Version header or directly use /api/v/{version}.",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = fl_openapi # OpenAPI schema setup

