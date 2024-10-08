import asyncio
import itertools
import logging
from typing import Dict

import websockets
from websockets.server import serve, WebSocketServer

from web.backend.constants import CloseReason, OpCode
from web.backend.message import ClientMessage, ServerMessage
from web.backend.manager import AsyncWebManager, AsyncioManagerPool
from utils import IncompleteMessageError, InvalidStartBytesError, NoManagerError


logger = logging.getLogger('__main__.' + __name__)


class WebsocketApp:
    _id_iter = itertools.count()

    def __init__(self) -> None:
        self.pool = AsyncioManagerPool(3, 10)
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
            logger.info('Server closed')

    def close(self):
        """Close the server and all managers"""
        self.pool.close()
        if self.server is not None:
            self.server.close()

    async def connection_handler(self, connection: websockets.WebSocketServerProtocol):
        """Handle new connections"""
        logger.info(f'New connection from {connection.remote_address}')
        current_message = b''
        client_id = None
        manager = None
        async for raw_message in connection:
            # Message Structure
            # 4 bytes: start
            # 4 bytes: length
            # 4 bytes: client_id
            # 4 bytes: Command
            # n bytes: raw_data
            # 4 bytes: checksum
            # 4 bytes: end

            logger.debug(f'Processing message from {connection.remote_address}')
            try:
                parsed_message = ClientMessage(current_message + raw_message)
            except InvalidStartBytesError:
                logger.warning(f'Message by {connection.remote_address} has invalid start bytes')
                continue
            except IncompleteMessageError:
                logger.debug(f'Message by {connection.remote_address} has incomplete message, waiting out for future messages')
                current_message += raw_message
                continue
            else:
                logger.debug(f'Parsed message from {connection.remote_address}: {parsed_message}')
                current_message = b''

            if client_id is None:
                # new connection
                client_id = next(self._id_iter)
                parsed_message.client_id = client_id

                try:
                    manager = await self.pool.get()
                except NoManagerError:
                    # No manager, try again later. Server at max capacity.
                    logger.warning(f'No managers available for {connection.remote_address}')
                    await ServerMessage(
                        OpCode.Server.CLOSE, client_id, integers=[CloseReason.NO_MANAGER]
                    ).send(connection)
                    await connection.close()
                    continue
                else:
                    manager.ws_connection = connection
                    self.connections[client_id] = manager

            parsed_message.execute_message(manager)
            await parsed_message.ack(connection)

        if manager is not None:
            await self.pool.release(manager)
        logger.info(f'Connection from {connection.remote_address} closed')
