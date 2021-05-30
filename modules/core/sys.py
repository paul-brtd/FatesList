from .imports import *

# Include all the modules by looping through and using importlib to import them and then including them in fastapi
def include_routers(fname, rootpath):
    for root, dirs, files in os.walk(rootpath):
        if not root.startswith("_") and not root.startswith("."):
            rrep = root.replace("/", ".")
            for f in files:
                if not f.startswith("_") and not f.startswith(".") and not f.endswith("pyc"):
                    path = f"{rrep}.{f.replace('.py', '')}"
                    logger.debug(f"{fname}: {root}: Loading {f} with path {path}")
                    route = importlib.import_module(path)
                    app.include_router(route.router)
