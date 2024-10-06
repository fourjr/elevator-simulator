import asyncio
import logging
import sys

from web.backend import WebsocketApp


logger = logging.getLogger(__name__)


def start_server(*args):
    app = WebsocketApp(*args)
    asyncio.run(app.start())


def setup_logger(logger):
    dt_fmt = r'%H:%M:%S'  # %Y-%m-%d
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[{asctime}] [{levelname:<5}] {name}: {message}', dt_fmt, style='{')
    handler.setFormatter(formatter)

    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)


if __name__ == '__main__':
    setup_logger(logger)
    start_server()
