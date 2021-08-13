"""Fates List Management"""
import sys
sys.pycache_prefix = "data/pycache"

from subprocess import Popen, DEVNULL
import os
import io
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
import click

@click.group()
def app():
    """Fates List Management"""
    pass

@click.group()
def site():
    """Fates List site management"""
    pass

@click.group()
def rabbit():
    """Fates List site management"""
    pass

@click.group()
def secrets():
    """Utilities to manage secrets"""
    pass

@click.group()
def staticfiles():
    """Utilities to manage static files"""

@click.group()
def db():
    """Utilities to manage databases such as backup etc."""


def error(ctx, msg: str, code: int = 1):
    click.secho(msg, fg="err", err=True)
    return ctx.exit(code=code)

def _fappgen(session_id, workers, static_assets):
    """Make the FastAPI app for gunicorn"""
    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse
    from modules.core.system import init_fates_worker
    from config import API_VERSION
     
    _app = FastAPI(
        title="Fates List",
        description="""
            Current API: v2 beta 3
            Default API: v2
            API Docs: https://apidocs.fateslist.xyz
            Enum Reference: https://apidocs.fateslist.xyz/structures/enums.autogen
        """,
        version="0.3.0",
        terms_of_service="https://fateslist.xyz/fates/tos",
        license_info={
            "name": "MIT",
            "url": "https://github.com/Fates-List/FatesList/blob/main/LICENSE"
        },
        default_response_class=ORJSONResponse, 
        redoc_url=f"/api/v{API_VERSION}/docs/redoc",
        docs_url=f"/api/v{API_VERSION}/docs/swagger",
        openapi_url=f"/api/v{API_VERSION}/docs/openapi",
        servers=[{"url": "https://fateslist.xyz", "description": "Fates List Main Server"}]
    )

    _app.state.static = static_assets

    @_app.on_event("startup")
    async def startup():
        await init_fates_worker(_app, session_id, workers)
    
    return _app


default_workers_num = (multiprocessing.cpu_count() * 2) + 1


@site.command("run")
@click.option("--workers", type=click.types.INT, default=default_workers_num, help="Amount of workers")
@click.pass_context
def run_site(ctx, workers):
    """Runs the Fates List site"""
    from gunicorn.app.base import BaseApplication
    from PIL import Image
    from config._logger import logger
    
    session_id = uuid.uuid4()
   
    # Load in static assets for bot widgets
    static_assets = {}
    with open("data/static/botlisticon.webp", mode='rb') as res:
        static_assets["fates_img"] = io.BytesIO(res.read())

    with open("data/static/votes.png", mode='rb') as res:
        static_assets["votes_img"] = io.BytesIO(res.read())

    with open("data/static/server.png", mode='rb') as res:
        static_assets["server_img"] = io.BytesIO(res.read())

    static_assets["fates_pil"] = Image.open(static_assets["fates_img"]).resize((10, 10))
    static_assets["votes_pil"] = Image.open(static_assets["votes_img"]).resize((15, 15))
    static_assets["server_pil"] = Image.open(static_assets["server_img"]).resize((15, 15))

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
        "pidfile": "data/pids/gunicorn.pid",
        "preload_app": True,
        "timeout": 120
    }
    
    app = _fappgen(str(session_id), workers, static_assets)
    try:
        FatesRunner(app, options).run()
    except BaseException as exc:
        logger.info(f"{type(exc).__name__}: {exc}")


@site.command("enums2md")
def site_enum2html():
    """Converts the enums in modules/models/enums.py into markdown. Mainly for apidocs creation"""
    enums = importlib.import_module("modules.models.enums")
    aenum = importlib.import_module("aenum")
    md = {}
    md_path = Path("data/res/base_enum.md")
    with md_path.open() as f:
        base_md = f.read()

    for key in enums.__dict__.keys():
        # Ignore internal or dunder keys
        if key.startswith("_") or key in ("IntEnum", "Enum"):
            continue
        
        v = enums.__dict__[key]
        if isinstance(v, aenum.EnumType):
            props = list(v)
            md[key] = {}
            md[key]["doc"] = "\n"
            md[key]["table"] = "| Name | Value | Description |\n| :--- | :--- | :--- |\n"
            if v.__doc__ and v.__doc__ != "An enumeration.":
                md[key]["doc"] = "\n" + v.__doc__ + "\n\n"
            md[key]["table"] += "\n".join([f"| {prop.name} | {prop.value} | {prop.__doc__} |" for prop in props])
    
    md = dict(sorted(md.items()))

    md_out = []
    for key in md.keys():
        md_out.append(f'## {key}\n{md[key]["doc"]}{md[key]["table"]}')

    click.echo(base_md + "\n" + "\n\n".join(md_out))

@site.command("reload")
@click.pass_context
def site_reload(ctx):
    """Get the PID of the running site and reloads the site"""
    try:
        with open("data/pids/gunicorn.pid") as guni_pid:
            pid = guni_pid.read().replace(" ", "").replace("\n", "")
           
            if not pid.isdigit():
                return error(
                    ctx,
                    "Invalid/corrupt PID file found (site/gunicorn.pid)"
                )
           
            pid = int(pid)
            os.kill(pid, signal.SIGHUP) 
    
    except FileNotFoundError:
        return error(
            ctx,
            "No PID file found. Is the site running?"
        )

@site.command("venv")
@click.option('--python', type=click.types.STRING, required=False, help="Python interpreter path", default="python3.10")
@click.option('--home', type=click.Path(exists=True, path_type=Path), required=False, help="Home directory for setup", default=Path.home())
def venv_setup(python, home):
    """Sets up a new venv deleting the old one"""
    from config._logger import logger
    logger.info("Backing up old venv")
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
    
@rabbit.command("run")
def rabbit_run():
    """Runs the Rabbit Worker"""
    from lynxfall.rabbit.launcher import run
    from modules.core.system import setup_db, setup_discord
    from config._logger import logger
    from config import worker_key
    
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
    click.echo(secrets_lib.token_urlsafe())


@secrets.command("mktemplate")
@click.option('-i', 'inp', type=click.Path(exists=True), required=True, help="Input config_secrets.py to template")
@click.option('-o', 'out', type=click.Path(exists=False), required=True, help="Output config_secrets_templates.py to template")
def secrets_mktemplate(inp, out):
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
        out_file = str(src_file).replace(".js", ".min.js").replace("src/", "prod/").replace("js/", "")
        click.echo(f"{src_file} -> {out_file}")
        cmd = [
            "google-closure-compiler", 
            "--js", str(src_file), 
            "--js_output_file", out_file
        ]
            
        with Popen(cmd, env=os.environ) as proc:
            proc.wait()
        
    for src_file in Path("data/static/assets/src").rglob("*.scss"):
        out_file = str(src_file).replace(".scss", ".min.css").replace("src/", "prod/").replace("css/", "")
        click.echo(f"{src_file} -> {out_file}")
        cmd = [
            "sass",
            "--style=compressed",
            str(src_file),
            out_file
        ]

        with Popen(cmd, env=os.environ) as proc:
            proc.wait()

    for img in Path("data/static/assets/src/img").rglob("*"):
        ext = str(img).split(".")[-1]
        out = str(img).replace("src/img/", "prod/").replace(f".{ext}", ".webp")
        print(f"{img} -> {out}")
            
        if ext == "webp":
            shutil.copy2(str(img), out)
        else:
            cmd = [
                "cwebp",
                "-quiet",
                "-q", "75",
                str(img),
                "-o",
                out
            ]

            with Popen(cmd, env=os.environ) as proc:
                proc.wait()


@db.command("backup")
def db_backup():
    """Backs up the Fates List database"""
    from config._logger import logger
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
@click.option('-m', "module", type=click.types.STRING, required=True, help="Input migration to apply")
def db_apply(module):
    """Apply Fates List database migration"""
    from config._logger import logger
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
@click.option('--user', "user_id", type=click.types.INT, required=True, help="Input user id to wipe")
def db_wipeuser(user_id):
    """Wipes a user account (e.g. Data Deletion Request)"""
    from config._logger import logger
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
@click.option('--home', type=click.Path(exists=True, path_type=Path), required=False, help="Home directory for setup", default=Path.home())
def db_setup(home):
    """Setup Snowfall (the Fates List database system)"""
    from config._logger import logger
    click.confirm(
        "Setting up Snowfall databases is a potentially destructive operation. Continue?",
        abort=True
    )
    logger.info("Preparing to setup snowtuft")

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
 

app.add_command(site)
app.add_command(rabbit)
app.add_command(secrets)
app.add_command(staticfiles)
app.add_command(db)
    
if __name__ == "__main__":
    app()
