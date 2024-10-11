from __future__ import annotations
import asyncio
import logging

import websockets

from utils.errors import IncompletePacketError, InvalidStartBytesError, NoManagerError
from web.backend.constants import CloseReason, ErrorCode, OpCode
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
        self._is_closing = False

    @property
    def address(self):
        return f'{self.protocol.remote_address[0]}:{self.protocol.remote_address[1]}'

    async def _parse_message(self, raw_message):
        """Parse a message from the client"""
        logger.debug(f'Processing message from {self.address}')
        try:
            try:
                packet = ClientPacket(self, self.current_message + raw_message)
            except InvalidStartBytesError:
                logger.warning(f'Message by {self.address} has invalid start bytes')
                await self.close()
                return
            except IncompletePacketError:
                logger.debug(f'Message by {self.address} has incomplete message, waiting out for future messages')
                self.current_message += raw_message
                return
            else:
                logger.debug(f'Parsed message from {self.address}: {packet}')
                self.current_message = b''

            if self.client_id is None:
                # new connection
                self.client_id = next(self.app._id_iter)
                packet.client_id = self.client_id

                try:
                    self.manager = await self.app.pool.get()
                except NoManagerError:
                    # No manager, try again later. Server at max capacity.
                    logger.warning(f'No managers available for {self.address}')
                    await ServerPacket(
                        OpCode.CLOSE, [CloseReason.NO_MANAGER]
                    ).send(self.protocol)

                    await self.close()
                    return
                else:
                    self.manager.ws_connection = self
                    self.app.connections[self.client_id] = self.manager

            if packet.command == OpCode.DASHBOARD:
                await packet.ack(
                    self.app.pool.min_managers,
                    self.app.pool.max_managers,
                    len(self.app.pool.taken_managers),
                    len(self.app.pool.managers),
                    len(self.app.connections),
                )
            else:
                await packet.execute_message()
        except Exception as e:
            await ServerPacket(OpCode.ERROR, [ErrorCode.UNEXPECTED_ERROR]).send(self.protocol)
            logger.exception(f'Error processing message from {self.address}', exc_info=e)

    @classmethod
    async def process_connection(cls, app, protocol):
        """Handle new connections"""
        self = cls(app, protocol)
        logger.info(f'New connection from {self.address}')

        # Ensure the connection is not idle
        async def receive_first_message():
            raw_message = await protocol.recv()
            await self._parse_message(raw_message)

        try:
            await asyncio.wait_for(receive_first_message(), timeout=1)
        except asyncio.TimeoutError:
            logger.debug(f'Connection from {self.address} timed out')
        except websockets.ConnectionClosedOK:
            pass
        else:
            # Connection verified to be active, continue processing as normal
            async for raw_message in protocol:
                await self._parse_message(raw_message)

        await self.close()

    async def close(self):
        """Closes the connection"""
        if self._is_closing:
            return
        self._is_closing = True

        if self.client_id is not None and self.client_id in self.app.connections:
            self.app.connections.pop(self.client_id)

        if self.manager is not None:
            await self.app.pool.release(self.manager)

        await self.protocol.close()
        logger.info(f'Connection from {self.address} closed')
