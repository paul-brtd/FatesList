import uvloop
uvloop.install()
from modules.core.system import init_fates_worker
from fastapi.responses import ORJSONResponse
from config import API_VERSION

import typer
import importlib
import uuid
from fastapi import FastAPI

app = typer.Typer()
site = typer.Typer()
app.add_typer(site, name="site")
rabbit = typer.Typer()
app.add_typer(rabbit, name="rabbit")


@site.command("run")
def run_site(
    workers: int = typer.Argument(3, envvar="SITE_WORKERS"),
    session_id: uuid.UUID = typer.Argument(uuid.uuid4(), envvar="SESSION_ID")
):

    # Setup FastAPI with required urls and orjson for faster json handling
    app = FastAPI(
        default_response_class = ORJSONResponse, 
        redoc_url = f"/api/v{API_VERSION}/docs/redoc", 
        docs_url = f"/api/v{API_VERSION}/docs/swagger", 
        openapi_url = f"/api/v{API_VERSION}/docs/openapi"
    )

    @app.on_event("startup")
    async def startup():
        await init_fates_worker(app, workers, session_id)
    

if __name__ == "__main__":
    app()
