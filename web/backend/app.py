import asyncio
import logging
from typing import Dict

import websockets
from websockets.server import serve, WebSocketServer

from web.backend.constants import CloseReason, OpCode
from web.backend.message import ClientMessage, ServerMessage
from web.backend.manager import AsyncWebManager, AsyncioManagerPool
from utils import IncompleteMessageError, InvalidStartBytesError


logger = logging.getLogger('__main__.' + __name__)


class WebsocketApp:
    def __init__(self) -> None:
        self.pool = AsyncioManagerPool(3, 10)
        self.connections: Dict[int, AsyncWebManager] = {}
        self.server: WebSocketServer = None

    async def connection_handler(self, connection: websockets.WebSocketServerProtocol):
        logger.debug(f'New connection from {connection.remote_address}')
        current_message = b''
        async for raw_message in connection:
            # Message Structure
            # 4 bytes: start
            # 4 bytes: length
            # 4 bytes: client_id
            # 4 bytes: Command
            # n bytes: raw_data
            # 4 bytes: checksum
            # 4 bytes: end

            try:
                parsed_message = ClientMessage.parse_message(current_message + raw_message)
            except InvalidStartBytesError``:
                logger.warning(f'Message by {connection.remote_address} has invalid start bytes')
                continue
            except IncompleteMessageError:
                logger.debug(f'Message by {connection.remote_address} has incomplete message, waiting out for future messages')
                current_message += raw_message
                continue
            else:
                logger.debug(f'Parsed message from {connection.remote_address}: {parsed_message}')
                current_message = b''

            if parsed_message.client_id not in self.connections:
                try:
                    self.connections[parsed_message.client_id] = await self.pool.get()
                    self.connections[parsed_message.client_id].ws_connection = connection
                except IndexError:
                    logger.warning(f'No managers available for {connection.remote_address}')
                    await ServerMessage(
                        OpCode.Server.CLOSE, parsed_message.client_id, integers=[CloseReason.NO_MANAGERS]
                    ).send(connection)
                    await connection.close()
                    continue

            manager = self.connections[parsed_message.client_id]
            parsed_message.execute_message(manager)
            await parsed_message.ack(connection)

    def close(self):
        self.pool.close()
        if self.server is not None:
            self.server.close()

    async def start(self, port=5555):
        try:
            logger.info(f'Starting server on ws://localhost:{port}')
            async with serve(self.connection_handler, "localhost", port) as self.server:
                await asyncio.Future()  # run forever
        except asyncio.CancelledError:
            logger.debug('Server cancelled')
        finally:
            self.close()
            logger.info('Server closed')
