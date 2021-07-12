"""Fates List Management"""
import subprocess
import os
import uuid
import signal
import builtins

import uvloop
import typer
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from config import worker_key, API_VERSION
from modules.core.system import init_fates_worker, setup_db, setup_discord


app = typer.Typer()
site = typer.Typer(
    help="Fates List site management"
)
app.add_typer(site, name="site")
rabbit = typer.Typer(
    help="Fates List Rabbit Worker management"
)
app.add_typer(rabbit, name="rabbit")


def _fappgen():
    """Make the FastAPI app for gunicorn"""
    uvloop.install()
     
    _app = FastAPI(
        default_response_class=ORJSONResponse, 
        redoc_url=f"/api/v{API_VERSION}/docs/redoc",
        docs_url=f"/api/v{API_VERSION}/docs/swagger",
        openapi_url=f"/api/v{API_VERSION}/docs/openapi"
    )

    @_app.on_event("startup")
    async def startup():
        await init_fates_worker(_app)
    
    return _app


@site.command("run")
def run_site(
    workers: int = typer.Argument(3, envvar="SITE_WORKERS")
):
    "Runs the Fates List site"
    session_id = uuid.uuid4()
    proc = subprocess.Popen(  # pylint: disable=consider-using-with
        " ".join([
            "gunicorn", "--log-level=debug", 
            "-p", "~/flmain.pid",
            "-k", "config._uvicorn.FatesWorker",
            "-b", "0.0.0.0:9999", 
            "-w", str(workers),
            "'manage:_fappgen()'"
        ]),
        shell=True,
        env=os.environ | {
            "LOGURU_LEVEL": "DEBUG",
            "SESSION_ID": str(session_id),
            "WORKERS": str(workers),
        }
    )

    def _kill(*args, **kwargs):  # pylint: disable=unused-argument
        pass

    signal.signal(signal.SIGINT, _kill)
    signal.signal(signal.SIGQUIT, _kill)
    signal.signal(signal.SIGTERM, _kill)
    proc.wait()


@rabbit.command("run")
def run_rabbit():
    """Runs the Rabbit Worker"""
    from lynxfall.rabbit.launcher import run  # pylint: disable=import-outside-toplevel
    async def on_startup(state, logger):
        """Function that will be executed on startup"""
        state.__dict__.update(( await setup_db() ))  # noqa: E201,E202
        state.client = ( await setup_discord() )["main"]  # noqa: E201,E202
        
        # For unfortunate backward compatibility 
        # with functions that havent ported yet
        builtins.db = state.postgres
        builtins.redis_db = state.redis
        builtins.rabbitmq_db = state.rabbit
        builtins.client = builtins.dclient = state.client
        logger.debug("Finished startup")

    async def on_prepare(state, logger):
        """Function that will prepare our worker"""
        logger.debug("Waiting for discord")
        return await state.client.wait_until_ready()

    async def on_stop(state, logger):
        """Function that will run on stop"""
        state.dying = True
        logger.debug("Running on_stop")

    async def on_error(*args, **kwargs):  # pylint: disable=unused-argument
        """Runs on error"""
        ...

    run(
        worker_key=worker_key, 
        backend_folder="modules/rabbitmq", 
        on_startup=on_startup, 
        on_prepare=on_prepare,
        on_stop=on_stop, 
        on_error=on_error
    )  
    
    
if __name__ == "__main__":
    app()
