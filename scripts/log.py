import logging
import sys


def setup_logger(logger: str) -> logging.Logger:
    log = logging.getLogger(logger)
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%(levelname)s] - %(asctime)s - %(name)s - %(message)s"
    )
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)

    return log
