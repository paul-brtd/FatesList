import os

from .config import *

if os.environ.get("RUNNING_MANAGER_FL"):
    from .manager import *
