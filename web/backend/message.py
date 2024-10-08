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
    command: OpCode
    raw_data: bytes

    _cursor: int = 0

    def __init__(self, raw_data) -> None:
        """Creates a client message from raw data and parses it
        If no error has been raised, the message is valid

        raw_data: bytes
            The raw message data from the websocket

        Raises: InvalidStartBytesError, IncompleteMessageError, InvalidChecksumError
        """
        self.raw_data = raw_data
        self._parse()

    def _parse(self) -> None:
        """Parses a client message and checks its validity
        If no error has been raised, the message is valid

        Message Structure
            4 bytes: start
            4 bytes: Command
            4 bytes: length (n)
            [
                4 bytes: client_id (may not exist if it is a register packet)
                n-4 bytes: raw_data
            ]
            4 bytes: checksum (length, client_id, raw_data)
            4 bytes: end

        Raises: InvalidStartBytesError, IncompleteMessageError, InvalidChecksumError
        """
        start_bytes = self._read_bytes(4)
        if start_bytes != PacketConstants.START_BYTES:
            raise InvalidStartBytesError

        if self.raw_data[-4:] != PacketConstants.END_BYTES:
            raise IncompleteMessageError

        self.command = OpCode.Client(self._read_int())

        self.length = self._read_int()

        if self.length + 4 * 5 != len(self.raw_data):
            raise IncompleteMessageError

        if not self._verify_checksum():
            raise InvalidChecksumError

        if self.command == OpCode.Client.REGISTER:
            self.client_id = None
        else:
            self.client_id = self._read_int()

    def _verify_checksum(self) -> bool:
        """Verifies the checksum of the message"""
        checksum_message = self.raw_data[8:-8]
        checksum = self.raw_data[-8:-4]
        expected_checksum = int(md5(checksum_message).hexdigest()[-3:], 16) % 10
        actual_checksum = b2i(checksum)
        return expected_checksum == actual_checksum

    def _read_bytes(self, length) -> bytes:
        """Reads the next n bytes from the message"""
        result = self.raw_data[self._cursor:self._cursor + length]
        self._cursor += length
        return result

    def _read_int(self) -> int:
        """Reads the next 4 bytes from the message as an integer"""
        return b2i(self._read_bytes(4))

    def execute_message(self, manager: ElevatorManager) -> None:
        """Executes the message on the manager"""
        match self.command:
            case OpCode.Client.ADD_ELEVATOR:
                manager.add_elevator(self._read_int())
            case OpCode.Client.REMOVE_ELEVATOR:
                manager.remove_elevator(self._read_int())
            case OpCode.Client.SET_FLOORS:
                manager.set_floors(self._read_int())
            case OpCode.Client.SET_SIMULATION_SPEED:
                manager.set_speed(self._read_int())
            case OpCode.Client.ADD_PASSENGER:
                manager.add_passenger(self._read_int(), self._read_int())
            case OpCode.Client.ADD_PASSENGERS:
                count = self._read_int()
                passengers = [(self._read_int(), self._read_int()) for _ in range(count)]
                manager.add_passengers(passengers)
            case OpCode.Client.SET_ALGORITHM:
                raise NotImplementedError
            case OpCode.Client.SET_MAX_LOAD:
                manager.set_max_load(self._read_int())
            case OpCode.Client.RESET:
                manager.reset()
            case OpCode.Client.REGISTER:
                manager.reset()
            case OpCode.Client.PAUSE:
                manager.pause()
            case OpCode.Client.RESUME:
                manager.play()

    async def ack(self, connection) -> None:
        """Sends an ACK message to the client"""
        await ServerMessage(OpCode.Server.ACK, self.client_id).send(connection)

    def __str__(self) -> str:
        """Returns a string representation of the message"""
        return f'<ClientMessage command={self.command.name} client_id={self.client_id} raw_data_len={len(self.raw_data)}>'


class ServerMessage:
    def __init__(
            self, command: OpCode.Server, client_id: int, *,
            integers: List[int] = None, raw_data: bytes = None
            ) -> None:
        """Creates a server message"""
        self.command = command
        self.client_id = client_id

        if integers is not None:
            self.data = b''.join(map(i2b, integers))
            if raw_data is not None:
                raise ValueError("Cannot have both integers and raw_data")
        elif raw_data is not None:
            if not isinstance(self.data, bytes):
                raise TypeError("raw_data must be bytes")
            self.data = raw_data
        else:
            self.data = b''

    @property
    def length(self) -> int:
        """Gets the length of the message data (client_id and raw_data)"""
        return 4 + len(self.data)

    @property
    def checksum(self) -> int:
        """Calculates the checksum of the message (length, client_id, raw_data)"""
        checksum_message = b''.join([
            i2b(self.length),
            i2b(self.client_id),
            self.data
        ])
        return int(md5(checksum_message).hexdigest()[-3:], 16) % 10

    async def send(self, connection):
        """Sends the message to the client"""
        try:
            await connection.send(bytes(self))
        except ConnectionClosed:
            print('connection closed before message could be sent')
            pass
        else:
            logger.debug(f'Sent message to {connection.remote_address}: {self}')

    def __bytes__(self) -> bytes:
        """Converts the message to bytes as per the message format

        Message Structure
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
            self.data,

            i2b(self.checksum),
            PacketConstants.END_BYTES,
        ])

    def __str__(self) -> str:
        """Returns a string representation of the message"""
        return f'<ServerMessage command={self.command.name} client_id={self.client_id} raw_data_len={len(self.data)}>'
