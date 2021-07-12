import typer
import importlib


app = typer.Typer()
site = typer.Typer()
app.add_typer(site, name="site")
rabbit = typer.Typer()
app.add_typer(rabbit, name="rabbit")


@site.command("run")
def run_site():
    app = FastAPI
    


if __name__ == "__main__":
    app()
