import os

from .config_secrets import *
from .config import *

if os.environ.get("RUNNING_MANAGER_FL"):
    from .manager import *
