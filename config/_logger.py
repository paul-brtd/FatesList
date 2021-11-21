import logging
import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, backtrace=False, diagnose=True)
logger.add("data/logs/full.log", rotation="500 MB")
logger.add("data/logs/error.log", rotation="500 MB", level = "ERROR", backtrace=True, diagnose=True)
