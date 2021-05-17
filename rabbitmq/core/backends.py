# Import all needed backends
import os, importlib

class Backends():
    def __init__(self):
        self.reload_index = {} # Maps backend path to queue
        self.rmq_backends = {}

    def add(self, path, queue, backend, name, description, reload):
        if not reload and queue in self.rmq_backends.keys():
            raise ValueError("Queue already exists and not in reload mode!")
        self.rmq_backends |= {queue: {"backend": backend, "name": name, "description": description}}
        self.reload_index[path] = queue

    def ackall(self, queue):
        try:
            return self.rmq_backends[queue]["backend"].__ack_all__
        except:
            return False

    def get(self, queue):
        return self.rmq_backends[queue]["backend"]

    def getname(self, queue):
        return self.rmq_backends[queue]["name"]

    def getall(self):
        return self.rmq_backends.keys()

    def load(self, path):
        logger.debug(f"Worker: Loading {path}")
        _backend = importlib.import_module(path)
        config = _backend.Config
        self.add(path = path, queue = config.queue, backend = _backend.backend, name = config.name, description = config.description, reload = False)

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
            self.add(path = path, queue = config.queue, backend = _backend.backend, name = config.name, description = config.description, reload = True)
        except Exception as exc:
            logger.warning(f"Reloading failed | {type(exc).__name__}: {exc}")
            raise exc

    def getpath(self, f):
        """Utility function to get the path given a .py file (or backend name)"""
        return "rabbitmq.backend." + f.replace(".py", "")
