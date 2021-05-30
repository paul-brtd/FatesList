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

@app.on_event("startup")
async def startup():
    await startup_tasks(app)

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

@app.middleware("http")
async def fateslist_request_handler(request: Request, call_next):
    return await routeware(app, fl_exception_handler, request, call_next)

app.openapi = fl_openapi(app) # OpenAPI schema setup

