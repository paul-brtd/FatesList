import os

from .config import *

if os.environ.get("MANAGER_BOT"):
    print("Loading additional imports")
    from .manager import *
