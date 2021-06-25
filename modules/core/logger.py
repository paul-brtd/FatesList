import builtins
import logging
import sys

from loguru import logger

logger.remove()
logger.add(sys.stderr, backtrace=True, diagnose=True)
logger.add("logs/full.log", rotation="500 MB")
logger.add("logs/error.log", rotation = "500 MB", level = "ERROR")
builtins.logger = logger

class InterceptHandler(logging.Handler):
    """
    Default handler from examples in loguru documentaion.
    See https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """

    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )

# Just in case we need it
for name in ("a", "b"):
    logging.getLogger(name).handlers = [InterceptHandler()]
