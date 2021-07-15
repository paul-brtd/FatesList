"""Fates List Management"""
from subprocess import Popen
import os
import uuid
import signal
import builtins
from pathlib import Path
import secrets as secrets_lib
import hashlib
import datetime
from getpass import getpass

import uvloop
import typer
import git 
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
db = typer.Typer(
    help="Utilities to manage databases such as backup etc."
)
app.add_typer(secrets, name="secrets")
app.add_typer(staticfiles, name="staticfiles")
app.add_typer(db, name="db")


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
    Path("data/pids").mkdir(exist_ok = True)
   
    for sig in (signal.SIGINT, signal.SIGQUIT, signal.SIGTERM):
        signal.signal(sig, lambda *args, **kwargs: ...)

    cmd = [
        "gunicorn", "--log-level=debug", 
        "-p", "data/pids/gunicorn.pid",
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
        with open("data/pids/gunicorn.pid") as guni_pid:
            pid = guni_pid.read().replace(" ", "").replace("\n", "")
           
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
            begin, _, end = line.split('"')
            out_lst.append("".join((begin, '""', end)))
        
    with open(out, "w") as out_f:
        out_f.write("\n".join(out_lst)) 


@staticfiles.command("relabel")
def staticfiles_relabel():
    """Relabels all labelled (rev*) static files)"""
    relabels = []
    for s_file in Path("static/assets").rglob("*.rev*.*"):
        if str(s_file).endswith(".hash"):
            continue

        sha = Path(f"{s_file}.hash")
        needs_relabel = False
        
        if not sha.exists():
            needs_relabel = True

        else:
            with sha.open() as sha_f:
                hash_req = sha_f.read()
                hash_req = hash_req.replace(" ", "").replace("\n", "")
            
            with s_file.open("rb") as static_f:
                file_contents = static_f.read()
                hasher_file = hashlib.sha512()
                hasher_file.update(file_contents)
                hash_got = hasher_file.hexdigest()

            if hash_req != hash_got:
                needs_relabel = True
        
        typer.echo(f"{s_file} needs relabel? {needs_relabel}")
        s_file.touch(exist_ok=True)

        if needs_relabel:
            # Get new file name
            new_fname = str(s_file).split(".")
            rev_id = int(new_fname[-2][3:]) + 1
            new_fname[-2] = f"rev{rev_id}"
            new_fname = ".".join(new_fname)
            relabels.append(new_fname)

            # Rename and make new hash file
            s_file_new = s_file.rename(new_fname)
            
            if sha.exists():
                sha.unlink()
            
            with s_file_new.open("rb") as static_f:
                file_contents = static_f.read()
                hasher_file = hashlib.sha512()
                hasher_file.update(file_contents)
                hash_got = hasher_file.hexdigest()

            with open(f"{s_file_new}.hash", "w") as sha_f:
                sha_f.write(hash_got)
            
            relabels.append(f"{s_file_new}.hash")

            typer.echo(
                f"Relabelled {s_file} to {s_file_new}!"
            )
    
    if relabels:
        print("Pushing to github")
        repo = git.Repo('.')
        repo.git.add(*relabels)
        repo.git.commit("-m", "Static file relabel")
        repo.remote(name='origin').push()


@db.command("backup")
def db_backup():
    """Backs up the Fates List database"""
    bak_id = datetime.datetime.now().strftime('%Y-%m-%d~%H:%M:%S')
    cmd = f'pg_dump -Fc > /backups/full-{bak_id}.bak'
    
    with Popen(cmd, shell=True, env=os.environ) as proc:
        proc.wait()
    
    try:
        Path("/backups/latest.bak").unlink()
    except FileNotFoundError:
        pass

    Path("/backups/latest.bak").symlink_to(f'/backups/full-{bak_id}.bak')
    cmd = f'pg_dump -Fc --schema-only --no-owner > /backups/schema-{bak_id}.bak'
    
    with Popen(cmd, shell=True, env=os.environ) as proc:
        proc.wait()
   
    conf_pwd = getpass(prompt="Enter rclone conf password: ")
    for bak_type in ("full", "schema"):
        cmd = f"rclone copy /backups/{bak_type}-{bak_id}.bak 'Fates List:fates_backups' "
        cmd += f"--password-command 'printf {conf_pwd}'"

        with Popen(cmd, env=os.environ, shell=True) as proc:
            proc.wait()


if __name__ == "__main__":
    app()
