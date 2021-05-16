# Import all needed backends
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
