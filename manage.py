import subprocess
import os
import typer
import importlib
import uuid
import asyncio
import uvloop
uvloop.install()

app = typer.Typer()
site = typer.Typer()
app.add_typer(site, name="site")
rabbit = typer.Typer()
app.add_typer(rabbit, name="rabbit")


def _fappgen():
    """Make the FastAPI app for gunicorn"""   
    from modules.core.system import init_fates_worker
    from fastapi.responses import ORJSONResponse
    from config import API_VERSION
    from fastapi import FastAPI 
     
    site = FastAPI(
        default_response_class = ORJSONResponse, 
        redoc_url = f"/api/v{API_VERSION}/docs/redoc",
        docs_url = f"/api/v{API_VERSION}/docs/swagger",
        openapi_url = f"/api/v{API_VERSION}/docs/openapi"
    )

    @site.on_event("startup")
    async def startup():
        await init_fates_worker(site)
    
    return site


@site.command("run")
def run_site(
    workers: int = typer.Argument(3, envvar="SITE_WORKERS")
):
    session_id = uuid.uuid4()
    os.execle(
        "python3.10", "-m", "gunicorn",
        "--log-level=debug", 
        "-p", "~/flmain.pid",
        "-k", "config._uvicorn.FatesWorker",
        "-b", "0.0.0.0:9999", 
        "-w", str(workers),
        "'manage:_fappgen()'",
        env = os.environ | {
            "LOGURU_LEVEL": "DEBUG",
            "SESSION_ID": str(session_id),
            "WORKERS": str(workers)
        }
    )

@rabbit.command("run")
def run_rabbit():
    from lynxfall.rabbit.launcher import run
    from modules.core.system import setup_discord, setup_db
    from config import TOKEN_MAIN
    from config import worker_key
  
    async def on_startup(state, logger):
        """Function that will be executed on startup"""
        state.__dict__.update(( await setup_db() ))
        state.client = ( await setup_discord() )["main"]
        
        # For unfortunate backward compatibility with functions that havent ported yet
        builtins.db, builtins.redis_db, builtins.rabbitmq_db = state.postgres, state.redis, state.rabbit
        builtins.client = builtins.dclient = state.client

    async def on_prepare(state, logger):
        """Function that will prepare our worker"""
        return await state.client.wait_until_ready()

    async def on_stop(state, logger):
        """Function that will run on stop"""
        pass

    async def on_error(state, logger, message, exc, exc_type, exc_context):
        pass

    run(
        worker_key = worker_key, 
        backend_folder = "modules/rabbitmq", 
        on_startup = on_startup, 
        on_prepare = on_prepare,
        on_stop = on_stop, 
        on_error = on_error
    )  
    
    
if __name__ == "__main__":
    app()
