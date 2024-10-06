import random
import logging
from dataclasses import dataclass
from hashlib import md5
from typing import List

from websockets import ConnectionClosed

from web.backend.constants import PacketConstants, OpCode
from models import ElevatorManager
from utils import InvalidStartBytesError, IncompleteMessageError, InvalidChecksumError, i2b, b2i


logger = logging.getLogger('__main__.' + __name__)


@dataclass
class ClientMessage:
    length: int
    client_id: int
    receiver: int
    command: OpCode
    raw_data: bytes

    _cursor: int = 0

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def _parse(self):
        """Message Structure
            4 bytes: start
            4 bytes: Command
            4 bytes: length (n)
            [
                4 bytes: client_id (may not exist if it is a register packet)
                n-4 bytes: raw_data
            ]
            4 bytes: checksum (length, client_id, raw_data)
            4 bytes: end
        """
        start_bytes = self.read_bytes(4)
        if start_bytes != PacketConstants.START_BYTES:
            raise InvalidStartBytesError

        if self.raw_data[-4:] != PacketConstants.END_BYTES:
            raise IncompleteMessageError

        self.command = OpCode.Client(self.read_int())

        self.length = self.read_int()

        if self.length + 4 * 5 != len(self.raw_data):
            raise IncompleteMessageError

        if not self.verify_checksum():
            raise InvalidChecksumError

        if self.command == OpCode.Client.REGISTER:
            self.client_id = random.randint(1, 2000)  # TODO
        else:
            self.client_id = self.read_int()

    def verify_checksum(self):
        checksum_message = self.raw_data[8:-8]
        checksum = self.raw_data[-8:-4]
        return int(md5(checksum_message).hexdigest(), 16) % 10 == b2i(checksum)

    def read_bytes(self, length):
        result = self.raw_data[self._cursor:self._cursor + length]
        self._cursor += length
        return result

    def read_int(self):
        result = b2i(self.raw_data[self._cursor:self._cursor + 4])
        self._cursor += 4
        return result

    def execute_message(self, manager: ElevatorManager):
        match self.command:
            case OpCode.Client.ADD_ELEVATOR:
                manager.add_elevator(self.read_int())
            case OpCode.Client.REMOVE_ELEVATOR:
                manager.remove_elevator(self.read_int())
            case OpCode.Client.SET_FLOORS:
                manager.set_floors(self.read_int())
            case OpCode.Client.SET_SIMULATION_SPEED:
                manager.set_speed(self.read_int())
            case OpCode.Client.ADD_PASSENGER:
                manager.add_passenger(self.read_int(), self.read_int())
            case OpCode.Client.ADD_PASSENGERS:
                count = self.read_int()
                passengers = [(self.read_int(), self.read_int()) for _ in range(count)]
                manager.add_passengers(passengers)
            case OpCode.Client.SET_ALGORITHM:
                raise NotImplementedError
            case OpCode.Client.SET_MAX_LOAD:
                manager.set_max_load(self.read_int())
            case OpCode.Client.RESET:
                manager.reset()
            case OpCode.Client.REGISTER:
                manager.reset()
            case OpCode.Client.PAUSE:
                manager.pause()
            case OpCode.Client.RESUME:
                manager.play()

    async def ack(self, connection):
        await ServerMessage(OpCode.Server.ACK, self.client_id).send(connection)

    @classmethod
    def parse_message(cls, raw_message):
        # Check if this is a valid message
        message = cls(raw_message)
        message._parse()

        return message

    def __str__(self) -> str:
        return f'<ClientMessage command={self.command.name} \
            client_id={self.client_id} raw_data_len={len(self.raw_data)}>'


class ServerMessage:
    def __init__(
            self, command: OpCode.Server, client_id: int, *,
            integers: List[int] = None, raw_data: bytes = None
            ):
        self.command = command
        self.client_id = client_id

        if integers is not None:
            self.raw_data = b''.join(map(i2b, integers))
            if raw_data is not None:
                raise ValueError("Cannot have both integers and raw_data")
        elif raw_data is not None:
            if not isinstance(self.raw_data, bytes):
                raise TypeError("raw_data must be bytes")
            self.raw_data = raw_data
        else:
            self.raw_data = b''

    @property
    def checksum(self) -> int:
        checksum_message = b''.join([
            i2b(self.length),
            i2b(self.client_id),
            self.raw_data
        ])
        return int(md5(checksum_message).hexdigest(), 16) % 10

    @property
    def length(self) -> int:
        """Gets the length of the message data (client_id and raw_data)"""
        return 4 + len(self.raw_data)

    async def send(self, connection):
        try:
            await connection.send(bytes(self))
        except ConnectionClosed:
            print('connection closed before message could be sent')
            pass
        else:
            logger.debug(f'Sent message to {connection.remote_address}: {self}')

    def __bytes__(self) -> bytes:
        """Message Structure
            4 bytes: start
            4 bytes: Command
            4 bytes: length (n)
            [
                4 bytes: client_id
                n-4 bytes: raw_data
            ]
            4 bytes: checksum (length, client_id, raw_data)
            4 bytes: end
        """
        return b''.join([
            PacketConstants.START_BYTES,
            i2b(self.command),
            i2b(self.length),

            i2b(self.client_id),
            self.raw_data,

            i2b(self.checksum),
            PacketConstants.END_BYTES,
        ])

    def __str__(self) -> str:
        return f'<ServerMessage command={self.command.name} \
            client_id={self.client_id} raw_data_len={len(self.raw_data)}>'
