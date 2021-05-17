# Import all needed backends
import os, importlib

class Backends():
    def __init__(self):
        self.reload_index = {} # Maps backend path to queue
        self.rmq_backends = {}

    def add(self, path, config, backend, reload):
        if not reload and config.queue in self.rmq_backends.keys():
            raise ValueError("Queue already exists and not in reload mode!")
        self.rmq_backends |= {config.queue: {"backend": backend, "config": config}}
        self.reload_index[path] = config.queue

    def ackall(self, queue):
        try:
            return self.rmq_backends[queue]["config"].ackall
        except:
            return False

    def get(self, queue):
        return self.rmq_backends[queue]["backend"]

    def getname(self, queue):
        return self.rmq_backends[queue]["config"].name

    def getdesc(self, queue):
        return self.rmq_backends[queue]["config"].description

    def getall(self):
        return self.rmq_backends.keys()

    def load(self, path):
        logger.debug(f"Worker: Loading {path}")
        _backend = importlib.import_module(path)
        config = _backend.Config
        self.add(path = path, config = config, backend = _backend.backend, reload = False)

    def loadall(self):
        """Load all backends"""
        for f in os.listdir("rabbitmq/backend"):
            if not f.startswith("_") and not f.startswith("."):
                self.load(self.getpath(f))

    def reload(self, backend):
        path = self.getpath(backend)
        logger.debug(f"Worker: Reloading {path}")
        try:
            queue = self.reload_index[path]
            _backend = importlib.import_module(path)
            importlib.reload(_backend)
            config = _backend.Config
            self.add(path = path, config = config, backend = _backend.backend, reload = True)
        except Exception as exc:
            logger.warning(f"Reloading failed | {type(exc).__name__}: {exc}")
            raise exc

    def getpath(self, f):
        """Utility function to get the path given a .py file (or backend name)"""
        return "rabbitmq.backend." + f.replace(".py", "")
