import asyncio
import itertools
import logging
from typing import Dict

import websockets
from websockets.server import serve, WebSocketServer

from web.backend.connection import WSConnection
from web.backend.manager import AsyncWebManager, AsyncioManagerPool


logger = logging.getLogger('__main__.' + __name__)


class WebsocketApp:
    _id_iter = itertools.count()

    def __init__(self) -> None:
        self.pool = AsyncioManagerPool(1,3)
        self.connections: Dict[int, AsyncWebManager] = {}
        self.server: WebSocketServer = None

    async def start(self, port=5555):
        """Start the server on the given port"""
        try:
            logger.info(f'Starting server on ws://localhost:{port}')
            async with serve(self.connection_handler, "localhost", port) as self.server:
                await asyncio.Future()  # run forever
        except asyncio.CancelledError:
            logger.debug('Server cancelled')
        finally:
            self.close()

    def close(self):
        """Close the server and all managers"""
        self.pool.close()
        if self.server is not None:
            self.server.close()
        logger.info('Server closed')

    async def connection_handler(self, connection: websockets.WebSocketServerProtocol):
        await WSConnection.process_connection(self, connection)
