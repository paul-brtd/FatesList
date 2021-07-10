# Internally used by funicorn for uvloop
from uvicorn.workers import UvicornWorker


class FatesWorker(UvicornWorker):
    CONFIG_KWARGS = {"loop": "uvloop", "interface": "asgi3", "ws_max_size": 1000000000, "lifespan": "on"}
