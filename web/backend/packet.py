from __future__ import annotations
import logging
from dataclasses import dataclass
from hashlib import md5
from typing import List, Tuple

from websockets import ConnectionClosed

from utils import InvalidStartBytesError, IncompletePacketError, InvalidChecksumError, i2b, b2i, algo_to_enum
from utils.errors import BadArgumentError, NoManagerError
from web.backend.constants import Algorithms, ErrorCode, PacketConstants, OpCode


logger = logging.getLogger('__main__.' + __name__)


@dataclass
class ClientPacket:
    length: int
    command: OpCode
    raw_data: bytes

    _cursor: int = 0

    def __init__(self, connection: 'WSConnection', raw_data) -> None:
        """Creates a client packet from raw data and parses it
        If no error has been raised, the packet is valid

        connection: WSConnection
            The connection object that the packet came from

        raw_data: bytes
            The raw message data from the websocket

        Raises: InvalidStartBytesError, IncompletePacketError, InvalidChecksumError
        """
        self.connection = connection
        self.raw_data = raw_data
        self._parse()

    def _parse(self) -> None:
        """Parses a client packet and checks its validity
        If no error has been raised, the message is valid

        Message Structure
            4 bytes: start
            2 bytes: Command
            2 bytes: length (n)
            [
                n bytes: data
            ]
            2 bytes: checksum (length, data)
            4 bytes: end

        Raises: InvalidStartBytesError, IncompletePacketError, InvalidChecksumError
        """
        start_bytes = self._read_bytes(4)
        if start_bytes != PacketConstants.START_BYTES:
            raise InvalidStartBytesError

        if self.raw_data[-4:] != PacketConstants.END_BYTES:
            raise IncompletePacketError

        self.command = OpCode(self._read_int())

        self.length = self._read_int()

        if self.length + 8 + 6 != len(self.raw_data):
            raise IncompletePacketError

        if not self._verify_checksum():
            raise InvalidChecksumError

    def _verify_checksum(self) -> bool:
        """Verifies the checksum of the packet"""
        checksum_message = self.raw_data[6:-6]
        checksum = self.raw_data[-6:-4]
        expected_checksum = int(md5(checksum_message).hexdigest()[-3:], 16) % 10
        actual_checksum = b2i(checksum)
        return expected_checksum == actual_checksum

    def _read_bytes(self, length) -> bytes:
        """Reads the next n bytes from the packet"""
        result = self.raw_data[self._cursor:self._cursor + length]
        self._cursor += length
        return result

    def _read_int(self) -> int:
        """Reads the next 2 bytes from the packet as an integer"""
        return b2i(self._read_bytes(2))

    def _read_str(self) -> int:
        """Read the next length bytes as an ascii string"""
        length = self._read_int()
        return self._read_bytes(length).decode('ascii')

    @property
    def data(self) -> Tuple[int]:
        """Returns the data of the packet as a list of integers"""
        return tuple((b2i(self.raw_data[n:n + 2])) for n in range(8, len(self.raw_data) - 6, 2))

    async def execute_message(self) -> None:
        """Executes the packet on the manager"""
        manager = self.connection.manager
        if manager is None:
            raise NoManagerError('No manager available for execution in execute_message')

        match self.command:
            case OpCode.ADD_ELEVATOR:
                current_floor = self._read_int()
                ev = manager.add_elevator(current_floor)
                await self.ack(ev.id)

            case OpCode.REMOVE_ELEVATOR:
                ev_id = self._read_int()
                try:
                    manager.remove_elevator(ev_id)
                except BadArgumentError:
                    await self.error(ErrorCode.BAD_ARGUMENT)
                else:
                    await self.ack()

            case OpCode.SET_FLOORS:
                floor_count = self._read_int()
                manager.set_floors(floor_count)
                await self.ack()

            case OpCode.SET_SIMULATION_SPEED:
                speed = self._read_int() / 100
                manager.set_speed(speed)
                await self.ack()

            case OpCode.SET_UPDATE_SPEED:
                speed = self._read_int() / 100
                self.connection.update_speed = speed  # TODO
                await self.ack()

            case OpCode.ADD_PASSENGERS:
                count = self._read_int()
                passengers = [(self._read_int(), self._read_int()) for _ in range(count)]
                manager.add_passengers(passengers)

                # flatten passengers
                await self.ack()

            case OpCode.SET_ALGORITHM:
                algorithm_id = self._read_int()
                algorithm_name = Algorithms(algorithm_id).name.replace('_', ' ')
                cls = manager.algorithms[algorithm_name]
                manager.set_algorithm(cls)

                await self.ack()

            case OpCode.SET_MAX_LOAD:
                max_load = self._read_int()
                manager.set_max_load(max_load)
                await self.ack()

            case OpCode.NEW_SIMULATION:
                manager.reset()
                # floors, max_load, algorithm_id, simulation_speed, update_speed
                await self.ack(
                    manager.algorithm.floors,
                    manager.algorithm.max_load,
                    algo_to_enum(manager.algorithm.__class__),
                    int(manager.speed * 100),
                    int(self.connection.update_speed * 100)
                )

            case OpCode.STOP_SIMULATION:
                manager.pause()
                await self.ack()

            case OpCode.START_SIMULATION:
                manager.start_simulation()
                await self.ack()

    async def ack(self, *additional_data: int | bytes | str) -> None:
        """Replies to the client with a server packet
        and the given data

        additional_data: int*
            Additional data to send at the front of the ACK packet
        """
        new_data = additional_data + self.data
        await ServerPacket(self.command, new_data).send(self.connection.protocol)

    async def error(self, error_code) -> None:
        """Sends an ERROR packet to the client"""
        await ServerPacket(OpCode.ERROR, [error_code]).send(self.connection.protocol)

    def __str__(self) -> str:
        """Returns a string representation of the packet"""
        return f'<ClientPacket command={self.command.name} data=[{", ".join(map(str, self.data))}]>'


class ServerPacket:
    def __init__(
        self, command: OpCode, data: List[int | bytes | str] = None
    ) -> None:
        """Creates a server packet"""
        self.command = command

        self.data = b''
        if data is not None:
            for n in data:
                if isinstance(n, int):
                    self.data += i2b(n)
                elif isinstance(n, bytes):
                    self.data += n
                elif isinstance(n, str):
                    self.data += i2b(len(n))
                    self.data += n.encode('ascii')
                else:
                    raise ValueError(f'Invalid data type {type(n)} in {data}')

    @property
    def length(self) -> int:
        """Gets the length of the packet data (raw_data)"""
        return len(self.data)

    @property
    def checksum(self) -> int:
        """Calculates the checksum of the packet (length, raw_data)"""
        checksum_message = b''.join([
            i2b(self.length),
            self.data
        ])
        return int(md5(checksum_message).hexdigest()[-3:], 16) % 10

    async def send(self, protocol):
        """Sends the packet to the client"""
        try:
            await protocol.send(bytes(self))
        except ConnectionClosed:
            print('connection closed before message could be sent')
            pass
        else:
            logger.debug(f'Sent message to {protocol.remote_address[0]}:{protocol.remote_address[1]}: {self}')

    def __bytes__(self) -> bytes:
        """Converts the packet to bytes as per the packet format

        Packet Structure
            4 bytes: start
            4 bytes: Command
            4 bytes: length (n)
            [
                n bytes: data
            ]
            4 bytes: checksum (length, data)
            4 bytes: end
        """
        return b''.join([
            PacketConstants.START_BYTES,
            i2b(self.command),
            i2b(self.length),

            self.data,

            i2b(self.checksum),
            PacketConstants.END_BYTES,
        ])

    def __str__(self) -> str:
        """Returns a string representation of the message"""
        integer_data = [str(b2i(self.data[n:n + 2])) for n in range(0, len(self.data), 2)]
        return f'<ServerPacket command={self.command.name} data=[{', '.join(integer_data)}]>'
