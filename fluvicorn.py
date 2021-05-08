# Internally used by funicorn for uvloop
from uvicorn.workers import UvicornWorker
class FatesWorker(UvicornWorker):
    CONFIG_KWARGS = {"loop": "uvloop"}
