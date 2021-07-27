"""Fates List Management"""
import sys
sys.pycache_prefix = "data/pycache"

from subprocess import Popen, DEVNULL
import os
os.environ["LOGURU_LEVEL"] = "DEBUG"

import uuid
import signal
import builtins
from pathlib import Path
import secrets as secrets_lib
import hashlib
import datetime
from getpass import getpass
import importlib
import asyncio
import shutil
import time
import multiprocessing
from typing import Any, Callable, Dict

from config._logger import logger
import typer
from config import worker_key, API_VERSION, TOKEN_MAIN, TOKEN_SERVER


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
app.add_typer(secrets, name="secrets")

staticfiles = typer.Typer(
    help="Utilities to manage static files"
)
app.add_typer(staticfiles, name="staticfiles")

db = typer.Typer(
    help="Utilities to manage databases such as backup etc."
)
app.add_typer(db, name="db")

venv = typer.Typer(
    help="Utilities to manage the Fates List VENV"
)
app.add_typer(venv, name="venv")


def error(msg: str, code: int = 1):
    typer.secho(msg, fg=typer.colors.RED, err=True)
    return typer.Exit(code=code)

def _fappgen(session_id, workers):
    """Make the FastAPI app for gunicorn"""
    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse
    from modules.core.system import init_fates_worker
     
    _app = FastAPI(
        title="Fates List",
        description="""
            Current API: v2 beta 3
            Default API: v2
            API Docs: https://apidocs.fateslist.xyz
        """,
        version="0.2.0",
        default_response_class=ORJSONResponse, 
        redoc_url=f"/api/v{API_VERSION}/docs/redoc",
        docs_url=f"/api/v{API_VERSION}/docs/swagger",
        openapi_url=f"/api/v{API_VERSION}/docs/openapi"
    )

    @_app.on_event("startup")
    async def startup():
        await init_fates_worker(_app, session_id, workers)
    
    return _app


default_workers_num = lambda: (multiprocessing.cpu_count() * 2) + 1


@site.command("run")
def run_site(
    workers: int = typer.Argument(default_workers_num, envvar="SITE_WORKERS"),
):
    """Runs the Fates List site"""
    from gunicorn.app.base import BaseApplication

    session_id = uuid.uuid4()
    
    # Create the pids folder if it hasnt been created
    Path("data/pids").mkdir(exist_ok = True)
   
    for sig in (signal.SIGINT, signal.SIGQUIT, signal.SIGTERM):
        signal.signal(sig, lambda *args, **kwargs: ...)
    
    class FatesRunner(BaseApplication):
        def __init__(self, application: Callable, options: Dict[str, Any] = {}):
            self.options = options
            self.application = application
            super().__init__()

        def load_config(self):
            config = {
                key: value
                for key, value in self.options.items()
                if key in self.cfg.settings and value is not None
            }
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

        def load(self):
            return self.application

    options = {
        "worker_class": "config._uvicorn.FatesWorker",
        "workers": workers,
        "bind": "0.0.0.0:9999",
        "loglevel": "debug",
        "pidfile": "data/pids/gunicorn.pid"
    }
    
    app = _fappgen(str(session_id), workers)
    FatesRunner(app, options).run()


@site.command("reload")
def site_reload():
    """Get the PID of the running site and reloads the site"""
    try:
        with open("data/pids/gunicorn.pid") as guni_pid:
            pid = guni_pid.read().replace(" ", "").replace("\n", "")
           
            if not pid.isdigit():
                return error(
                    "Invalid/corrupt PID file found (site/gunicorn.pid)"
                )
           
            pid = int(pid)
            os.kill(pid, signal.SIGHUP) 
    
    except FileNotFoundError:
        return error(
            "No PID file found. Is the site running?"
        )

@rabbit.command("run")
def rabbit_run():
    """Runs the Rabbit Worker"""
    from lynxfall.rabbit.launcher import run
    from modules.core.system import setup_db, setup_discord
    
    async def on_startup(state, logger):
        """Function that will be executed on startup"""
        state.__dict__.update(( await setup_db() ))  # noqa: E201,E202
        state.discord = setup_discord()
        state.client = state.discord["main"]  # noqa: E201,E202
        
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
        logger.info("Going home!")

    async def on_error(*_, **__):  # pylint: disable=unused-argument
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


@staticfiles.command("compile")
def staticfiles_compile():
    """Compiles all labelled static files"""
    for src_file in Path("data/static/assets/src").rglob("*.js"):
        print(src_file)
        cmd = [
            "google-closure-compiler", 
            "--js", str(src_file), 
            "--js_output_file", str(src_file).replace(".js", ".min.js").replace("src/", "prod/")
        ]
            
        with Popen(cmd, env=os.environ) as proc:
            proc.wait()
    
    for src_file in Path("data/static/assets/src").rglob("*.scss"):
        print(src_file)
        cmd = [
            "sass",
            "--style=compressed",
            str(src_file),
            str(src_file).replace(".scss", ".min.css").replace("src/", "prod/")
        ]

        with Popen(cmd, env=os.environ) as proc:
            proc.wait()

        for img in Path("data/static/assets/src/img").rglob("*"):
            shutil.copy(str(img), str(img).replace("src/img/", "prod/"))

@db.command("backup")
def db_backup():
    """Backs up the Fates List database"""
    logger.info("Starting backups")

    bak_id = datetime.datetime.now().strftime('%Y-%m-%d~%H:%M:%S')
    cmd = f'pg_dump -Fc > /backups/full-{bak_id}.bak'
    
    with Popen(cmd, shell=True, env=os.environ) as proc:
        proc.wait()
    
    logger.info("Backup of full db done. Backing up only schema...")

    try:
        Path("/backups/latest.bak").unlink()
    except FileNotFoundError:
        pass

    Path("/backups/latest.bak").symlink_to(f'/backups/full-{bak_id}.bak')
    cmd = f'pg_dump -Fc --schema-only --no-owner > /backups/schema-{bak_id}.bak'
    
    with Popen(cmd, shell=True, env=os.environ) as proc:
        proc.wait()

    logger.info("Schema backup done")
   
    conf_pwd = getpass(prompt="Enter rclone conf password: ")
    for bak_type in ("full", "schema"):
        cmd = f"rclone copy /backups/{bak_type}-{bak_id}.bak 'Fates List:fates_backups' "
        cmd += f"--password-command 'printf {conf_pwd}'"

        with Popen(cmd, env=os.environ, shell=True) as proc:
            proc.wait()
    
    logger.success("Backups done!")

@db.command("shell")
def db_shell():
    """Run a postgres shell"""
    with Popen(["pgcli"], env=os.environ) as proc:
        proc.wait()


@db.command("apply")
def db_apply(module: str):
    """Apply Fates List database migration"""
    import uvloop
    uvloop.install()
    
    import asyncpg
    import aioredis
    
    try:
        migration = importlib.import_module(module)
        _ = migration.apply # Check for apply function
    except Exception as exc:
        return error(
            f"Could not import migration file: {exc}"
        )

    async def _migrator():
        postgres = await asyncpg.create_pool()
        redis = aioredis.from_url('redis://localhost:1001', db=1)
        logger.info("Starting migration")
        ret = await migration.apply(postgres=postgres, redis=redis, logger=logger)
        logger.success(f"Migration applied with return code of {ret}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_migrator())


@db.command("wipeuser")
def db_wipeuser(user_id: int):
    """Wipes a user account (e.g. Data Deletion Request)"""
    import uvloop
    uvloop.install()
    
    import asyncpg
    import aioredis
    
    async def _wipeuser():
        logger.info("Wiping user info in db")
        db = await asyncpg.create_pool()
        await db.execute("DELETE FROM users WHERE user_id = $1", user_id)
        await db.execute("INSERT INTO users (user_id, vote_epoch) VALUES ($1, NOW())", user_id) # INSERT minimal data to prevent abuse
        
        bots = await db.fetch(
            """SELECT DISTINCT bots.bot_id FROM bots 
            INNER JOIN bot_owner ON bot_owner.bot_id = bots.bot_id 
            WHERE bot_owner.owner = $1 AND bot_owner.main = true""", 
            user_id
        )
        for bot in bots:
            await db.execute("DELETE FROM bots WHERE bot_id = $1", bot["bot_id"])
            
        votes = await db.fetch("SELECT bot_id from bot_voters WHERE user_id = $1", user_id)
        for vote in votes:
            await db.execute("UPDATE bots SET votes = votes - 1 WHERE bot_id = $1", vote["bot_id"])
            
        await db.execute("DELETE FROM bot_voters WHERE user_id = $1", user_id)
           
        logger.info("Clearing redis info on user...")
        redis = aioredis.from_url('redis://localhost:1001', db=1)
        await redis.hdel(str(user_id), 'cache')
        await redis.hdel(str(user_id), 'ws')
        
        await redis.close()
        logger.success("Done wiping user")
        
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_wipeuser())
    

@db.command("setup")
def db_setup(
    primary_user: str = typer.Argument("meow", envvar="HOME_DIR")
):
    """Setup Snowfall (the Fates List database system)"""
    typer.confirm(
        "Setting up Snowfall databases is a potentially destructive operation. Continue?",
        abort=True
    )
    logger.info("Preparing to setup snowtuft")
    
    home = Path("/home") / primary_user

    if not home.exists():
        return error("Invalid user specified for primary_user")

    with open("/etc/sysctl.conf", "w") as sysctl_file:
        lines = [
            "fs.file-max=17500",
            "vm.overcommit_memory = 1"
        ]
        sysctl_file.write("\n".join(lines))
    
    with Popen(["sysctl", "-p"], env=os.environ, stdout=DEVNULL) as proc:
        proc.wait()
    
    if Path("/snowfall/docker/env_done").exists():
        logger.info("Existing docker setup found. Backing it up...")
        try:
            db_backup()
        except Exception as exc:
            logger.error(f"Backup failed. Error is {exc}")
            typer.confirm("Continue? ", abort=True)

        with Popen(["systemctl", "stop", "snowfall-dbs"], env=os.environ) as proc:
            proc.wait()
    
    logger.info("Removing/Renaming old files")
    
    def _rm_force(f_name):
        try:
            Path(f_name).unlink()
        except Exception:
            pass
    
    _rm_force("/etc/systemd/system/snowfall-dbs.service")
    
    if Path("/snowfall").exists():
        id = str(uuid.uuid4())
        logger.info(f"Moving /snowfall to /snowfall.old/{id}")
        Path("/snowfall.old").mkdir(exist_ok=True)
        Path("/snowfall").rename(f"/snowfall.old/{id}")
    
    Path("/snowfall/docker/db/postgres").mkdir(parents=True)
    Path("/snowfall/docker/db/redis").mkdir(parents=True)
    Path("/snowfall/docker/db/rabbit").mkdir(parents=True)
    
    pg_pwd = secrets_lib.token_urlsafe()
    
    with open("/snowfall/docker/env.pg", "w") as env_pg:
        lines = [
            "POSTGRES_DB=fateslist",
            "POSTGRES_USER=fateslist",
            f"POSTGRES_PASSWORD={pg_pwd}"
        ]
        env_pg.write("\n".join(lines))
    
    erlang_shared_cookie = secrets_lib.token_urlsafe()
    
    with open("/snowfall/docker/env.rabbit", "w") as env_rabbit:
        lines = [
            "NODENAME=fateslist_rabbit",
            f"RABBITMQ_ERLANG_COOKIE={erlang_shared_cookie}"
        ]
        env_rabbit.write("\n".join(lines))
    
    shutil.copytree("data/snowfall/docker/scripts", "/snowfall/docker/scripts", dirs_exist_ok=True)
    shutil.copy2("data/snowfall/docker/config/docker-compose.yml", "/snowfall/docker")
    
    logger.info("Starting up docker compose...")
    cmd = [
        "docker-compose", 
        "-f",
        "/snowfall/docker/docker-compose.yml",
        "up",
        "-d"
    ]
    
    with Popen(cmd, env=os.environ) as proc:
        proc.wait()
    
    time.sleep(5)
    
    logger.info("Fixing postgres password. Do not worry if this fails")
    
    cmd = [
        "docker", "exec", "snowfall.postgres", 
        "psql", "-U", "fateslist", 
        "-d", "fateslist", 
        "-c", f"ALTER USER fateslist WITH PASSWORD '{pg_pwd}'"
    ]
    
    with Popen(cmd, env=os.environ) as proc:
        proc.wait()
    
    for op in ("start", "stop"):
        script_path = Path(f"/usr/bin/snowfall-dbs-{op}")
        with script_path.open("w") as action_script:
            lines = [
                "#!/bin/bash",
                f"/usr/bin/docker {op} snowfall.postgres",
                f"/usr/bin/docker {op} snowfall.redis",
                f"/usr/bin/docker {op} snowfall.rabbit"
            ]
            action_script.write("\n".join(lines))
            
        script_path.chmod(755)
        
    with open("/etc/systemd/system/snowfall-dbs.service", "w") as sf_service:
        lines = [
            "[Unit]",
            "Description=Docker Compose Snowfall 2.0",
            "Requires=docker.service",
            "After=docker.service",
            "",
            "[Service]",
            "Type=oneshot",
            "RemainAfterExit=yes",
            "WorkingDirectory=/snowfall/docker",
            "ExecStart=/usr/bin/snowfall-dbs-start",
            "ExecStop=/usr/bin/snowfall-dbs-stop"
            "TimeoutStartSec=0",
            "",
            "[Install]",
            "WantedBy=multi-user.target"
        ]
        
        sf_service.write("\n".join(lines))
    
    cmds = (
        ["systemctl", "daemon-reload"], 
        ["snowfall-dbs-stop"],
        ["systemctl", "start", "snowfall-dbs"],
        ["systemctl", "restart", "snowfall-dbs"]
    )
    
    for cmd in cmds:
        with Popen(cmd, env=os.environ) as proc:
            proc.wait()
    
    time.sleep(2)
    
    logger.info("Fixing up user env")
    
    with open("/snowfall/userenv", "w") as sf_userenv:
        lines = [
            "source /etc/profile",
            "export PGUSER=fateslist",
            "export PGHOST=localhost",
            "export PGPORT=1000",
            f"export PGPASSWORD='{pg_pwd}'",
            "export PGDATABASE=fateslist"
        ]
        
        sf_userenv.write("\n".join(lines))
    
    with Path(home / ".bashrc").open("a") as bashrc_f:
        lines = [
            "source /snowfall/userenv",
        ]
        
        bashrc_f.write("\n".join(lines))
    
    with open("/root/.bashrc", "w") as bashrc_f:
        lines = [
            "source /snowfall/userenv"
        ]
    
        bashrc_f.write("\n".join(lines))
    
    if Path("/backups/latest.bak").exists():
        
        logger.info("Restoring backup...")
        
        with open("/tmp/s2.bash", "w") as sf_s2_f:
            lines = [
                "source /snowfall/userenv",
                'psql -c "CREATE ROLE meow"',
                'psql -c "CREATE ROLE readaccess"',
                'psql -c "CREATE ROLE postgres"',
                'psql -c "CREATE ROLE root"',
                'psql -c "CREATE SCHEMA IF NOT EXISTS public"',
                "psql -c 'CREATE EXTENSION IF NOT EXISTS " + '"uuid-ossp"' + "'",
                "pg_restore -cvd fateslist /backups/latest.bak"
            ]
            sf_s2_f.write("\n".join(lines))
            
        with Popen(["bash", "/tmp/s2.bash"]) as proc:
            proc.wait()
            
    Path("/snowfall/docker/env_done").touch()
    logger.info(f"Postgres password is {pg_pwd}")
    logger.info(f"Erlang shared cookie is {erlang_shared_cookie}")
    logger.success("Done setting up databases")
    
 
@venv.command("setup")
def venv_setup(
    python: str = typer.Argument("python3.10", envvar="PYTHON")
):
    logger.info("Backing up old venv")
    home = Path.home()
    Path(home / "flvenv").rename(home / "flvenv.old")
    
    cmd = [
        python,
        "-m", 
        "venv", 
        str(home / "flvenv")
    ]
    
    with Popen(cmd, env=os.environ) as proc:
        proc.wait()
    
    new_python = home / "flvenv/bin/python"
    
    
if __name__ == "__main__":
    app()
