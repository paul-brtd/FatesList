import subprocess
import typer
import importlib
import uuid

app = typer.Typer()
site = typer.Typer()
app.add_typer(site, name="site")
rabbit = typer.Typer()
app.add_typer(rabbit, name="rabbit")


@site.command("run")
def run_site(
    workers: int = typer.Argument(3, envvar="SITE_WORKERS")
):
    session_id = uuid.uuid4()
    subprocess.Popen([
        "python3.10", "-m", "gunicorn",
        "--log-level=debug",
        "-p", "~/flmain.pid",
        "-k", "config._uvicorn.FatesWorker",
        "'manage:_fappgen()'",
        "-b", "0.0.0.0:9999",
        "-w", str(workers)
    ], env = {
        "LOGURU_LEVEL": "DEBUG",
        "SESSION_ID": session_id,
        "WORKERS": str(workers)
    })
    
def _fappgen():
    """Make the FastAPI app for gunicorn"""
    
    import uvloop
    uvloop.install()
    from modules.core.system import init_fates_worker
    from fastapi.responses import ORJSONResponse
    from config import API_VERSION
    from fastapi import FastAPI 
    
   
    _app = FastAPI(
        default_response_class = ORJSONResponse, 
        redoc_url = f"/api/v{API_VERSION}/docs/redoc", 
        docs_url = f"/api/v{API_VERSION}/docs/swagger", 
        openapi_url = f"/api/v{API_VERSION}/docs/openapi"
    )

    @_app.on_event("startup")
    async def startup():
        await init_fates_worker(_app)
    
    return _app

if __name__ == "__main__":
    app()
