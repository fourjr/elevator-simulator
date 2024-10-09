from __future__ import annotations
import asyncio
import logging

import websockets

from utils.errors import IncompletePacketError, InvalidStartBytesError, NoManagerError
from web.backend.constants import CloseReason, OpCode
from web.backend.packet import ClientPacket, ServerPacket


logger = logging.getLogger('__main__.' + __name__)


class WSConnection:
    def __init__(self, app: 'WebsocketApp', connection: websockets.WebSocketServerProtocol):
        self.app = app
        self.protocol = connection
        self.current_message = b''
        self.client_id = None
        self.manager = None
        self.update_speed = 1

    async def _parse_message(self, raw_message):
        """Parse a message from the client"""
        logger.debug(f'Processing message from {self.protocol.remote_address}')
        try:
            parsed_message = ClientPacket(self.current_message + raw_message)
        except InvalidStartBytesError:
            logger.warning(f'Message by {self.protocol.remote_address} has invalid start bytes')
            await self.close()
            return
        except IncompletePacketError:
            logger.debug(f'Message by {self.protocol.remote_address} has incomplete message, waiting out for future messages')
            self.current_message += raw_message
            return
        else:
            logger.debug(f'Parsed message from {self.protocol.remote_address}: {parsed_message}')
            self.current_message = b''

        if self.client_id is None:
            # new connection
            self.client_id = next(self.app._id_iter)
            parsed_message.client_id = self.client_id

            try:
                self.manager = await self.app.pool.get()
            except NoManagerError:
                # No manager, try again later. Server at max capacity.
                logger.warning(f'No managers available for {self.protocol.remote_address}')
                await ServerPacket(
                    OpCode.Server.CLOSE, [CloseReason.NO_MANAGER]
                ).send(self.protocol)

                await self.close()
                return
            else:
                self.manager.ws_connection = self
                self.app.connections[self.client_id] = self.manager

        await parsed_message.execute_message(self.manager)

    @classmethod
    async def process_connection(cls, app, protocol):
        """Handle new connections"""
        self = cls(app, protocol)
        logger.info(f'New connection from {protocol.remote_address}')

        # Ensure the connection is not idle
        async def receive_first_message():
            raw_message = await protocol.recv()
            await self._parse_message(raw_message)

        try:
            await asyncio.wait_for(receive_first_message(), timeout=1)
        except asyncio.TimeoutError:
            logger.debug(f'Connection from {protocol.remote_address} timed out')
        except websockets.ConnectionClosedOK:
            pass
        else:
            # Connection verified to be active, continue processing as normal
            async for raw_message in protocol:
                await self._parse_message(raw_message)

        await self.close()

    async def close(self):
        """Closes the connection"""
        if self.client_id is not None and self.client_id in self.app.connections:
            self.app.connections.pop(self.client_id)

        if self.manager is not None:
            await self.app.pool.release(self.manager)

        await self.protocol.close()
        logger.info(f'Connection from {self.protocol.remote_address} closed')
