"""Fates List Management"""
from subprocess import Popen
import os
import uuid
import signal
import builtins
from pathlib import Path
import secrets as secrets_lib

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
secrets = typer.Typer(
    help="Utilities to manage secrets"
)
staticfiles = typer.Typer(
    help="Utilities to manage static files"
)
app.add_typer(secrets, name="secrets")
app.add_typer(staticfiles, name="staticfiles")


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
    
    # Create the pids folder if it hasnt been created
    Path("pids").mkdir(exist_ok = True)
   
    for sig in (signal.SIGINT, signal.SIGQUIT, signal.SIGTERM):
        signal.signal(sig, lambda *args, **kwargs: ...)

    cmd = [
        "gunicorn", "--log-level=debug", 
        "-p", "pids/gunicorn.pid",
        "-k", "config._uvicorn.FatesWorker",
        "-b", "0.0.0.0:9999", 
        "-w", str(workers),
        "manage:_fappgen()"
    ]
    
    env=os.environ | {
        "LOGURU_LEVEL": "DEBUG",
        "SESSION_ID": str(session_id),
        "WORKERS": str(workers),
    }

    with Popen(cmd, env=env) as proc:
        proc.wait()


@site.command("reload")
def site_reload():
    """Get the PID of the running site and reloads the site"""
    try:
        with open("pids/gunicorn.pid") as f:
            pid = f.read().replace(" ", "").replace("\n", "")
           
            if not pid.isdigit():
                typer.secho(
                    "Invalid/corrupt PID file found (site/gunicorn.pid)",
                    fg=typer.colors.RED,
                    err=True
                )
                typer.Exit(code=1)
           
            pid = int(pid)
            os.kill(pid, signal.SIGHUP) 
    
    except FileNotFoundError:
        typer.secho(
            "No PID file found. Is the site running?",
            fg=typer.colors.RED,
            err=True
        )
        typer.Exit(code=1)

@rabbit.command("run")
def rabbit_run():
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
 

@secrets.command("random")
def secrets_random():
    """Generates a random secret"""
    typer.echo(secrets_lib.token_urlsafe())


@secrets.command("mktemplate")
def secrets_mktemplate(
    inp: str = typer.Argument(
        "config/config_secrets.py", 
        envvar="CFG_IN"
    ),
    out: str = typer.Argument(
        "config/config_secrets_template.py", 
        envvar="CFG_OUT"
    )
):
    """Converts config_secrets.py to config_secrets_template.py"""
    with open(inp) as inp_f:
        lines = inp_f.read()

    out_lst = []
    
    for line in lines.split("\n"):
        if line.replace(" ", ""):
            if line.startswith(("if:", "else:")):
                out_lst.append(line)
                continue
        
            # Remove middle part/secret
            begin, secret, end = line.split('"')
            out_lst.append("".join((begin, '""', end)))
        
    with open(out, "w") as out_f:
        out_f.write("\n".join(out_lst)) 


@staticfiles.command("relabel")
def staticfiles_relabel():
    for p in Path("static/assets").glob


if __name__ == "__main__":
    app()
