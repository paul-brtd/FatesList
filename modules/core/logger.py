from loguru import logger
import sys
import builtins
logger.remove()
logger.add(sys.stderr, backtrace=True, diagnose=True)
logger.add("logs/full.log", rotation="500 MB")
logger.add("logs/error.log", rotation = "500 MB", level = "ERROR")
builtins.logger = logger
