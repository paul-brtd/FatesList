from .backends import *
from .process import *
import importlib
import builtins

builtins.dbg = importlib.import_module(".debug", package = "rabbitmq.core")
