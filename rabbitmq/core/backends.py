# Import all needed backends
import os, importlib

class Backends():
    def __init__(self):
        self.rmq_backends = {}

    def add(self, queue, backend, name, description):
        self.rmq_backends |= {queue: {"backend": backend, "name": name, "description": description}}

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

    def load(self):
        """Load all backends"""
        for f in os.listdir("rabbitmq/backend"):
            if not f.startswith("_") and not f.startswith("."):
                path = "rabbitmq.backend." + f.replace(".py", "")
                logger.debug("Worker: Loading " + f.replace(".py", "") + " with path " + path)
                _backend = importlib.import_module(path)
                self.add(queue = _backend.queue, backend = _backend.backend, name = _backend.name, description = _backend.description)

