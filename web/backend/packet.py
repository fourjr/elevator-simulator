from __future__ import annotations
import logging
from dataclasses import dataclass
from hashlib import md5
from typing import List

from websockets import ConnectionClosed

from models.algorithm import ElevatorAlgorithm
from utils import InvalidStartBytesError, IncompletePacketError, InvalidChecksumError, i2b, b2i, algo_to_enum
from utils.errors import BadArgumentError
from web.backend.constants import Algorithms, ErrorCode, PacketConstants, OpCode


logger = logging.getLogger('__main__.' + __name__)


@dataclass
class ClientPacket:
    length: int
    command: OpCode
    raw_data: bytes

    _cursor: int = 0

    def __init__(self, raw_data) -> None:
        """Creates a client packet from raw data and parses it
        If no error has been raised, the packet is valid

        raw_data: bytes
            The raw message data from the websocket

        Raises: InvalidStartBytesError, IncompletePacketError, InvalidChecksumError
        """
        self.raw_data = raw_data
        self._parse()

    def _parse(self) -> None:
        """Parses a client packet and checks its validity
        If no error has been raised, the message is valid

        Message Structure
            4 bytes: start
            4 bytes: Command
            4 bytes: length (n)
            [
                n bytes: data
            ]
            4 bytes: checksum (length, data)
            4 bytes: end

        Raises: InvalidStartBytesError, IncompletePacketError, InvalidChecksumError
        """
        start_bytes = self._read_bytes(4)
        if start_bytes != PacketConstants.START_BYTES:
            raise InvalidStartBytesError

        if self.raw_data[-4:] != PacketConstants.END_BYTES:
            raise IncompletePacketError

        self.command = OpCode.Client(self._read_int())

        self.length = self._read_int()

        if self.length + 4 * 5 != len(self.raw_data):
            raise IncompletePacketError

        if not self._verify_checksum():
            raise InvalidChecksumError

    def _verify_checksum(self) -> bool:
        """Verifies the checksum of the packet"""
        checksum_message = self.raw_data[8:-8]
        checksum = self.raw_data[-8:-4]
        expected_checksum = int(md5(checksum_message).hexdigest()[-3:], 16) % 10
        actual_checksum = b2i(checksum)
        return expected_checksum == actual_checksum

    def _read_bytes(self, length) -> bytes:
        """Reads the next n bytes from the packet"""
        result = self.raw_data[self._cursor:self._cursor + length]
        self._cursor += length
        return result

    def _read_int(self) -> int:
        """Reads the next 4 bytes from the packet as an integer"""
        return b2i(self._read_bytes(4))

    async def execute_message(self, manager: 'AsyncWebManager') -> None:
        """Executes the packet on the manager"""
        match self.command:
            case OpCode.Client.ADD_ELEVATOR:
                current_floor = self._read_int()
                ev = manager.add_elevator(current_floor)
                await self.reply(
                    OpCode.Server.ADD_ELEVATOR, manager.ws_connection.protocol,
                    [ev.id, ev.current_floor]
                )

            case OpCode.Client.REMOVE_ELEVATOR:
                ev_id = self._read_int()
                try:
                    manager.remove_elevator(ev_id)
                except BadArgumentError:
                    await self.reply(
                        OpCode.Server.ERROR, manager.ws_connection.protocol,
                        [ErrorCode.BAD_ARGUMENT]
                    )
                else:
                    await self.reply(
                        OpCode.Server.REMOVE_ELEVATOR, manager.ws_connection.protocol,
                        [ev_id]
                    )

            case OpCode.Client.SET_FLOORS:
                floor_count = self._read_int()
                manager.set_floors(floor_count)
                await self.reply(
                    OpCode.Server.SET_FLOORS, manager.ws_connection.protocol,
                    [floor_count]
                )

            case OpCode.Client.SET_SIMULATION_SPEED:
                speed = self._read_int() / 100
                manager.set_speed(speed)
                await self.reply(
                    OpCode.Server.SET_SIMULATION_SPEED, manager.ws_connection.protocol,
                    [speed * 100]
                )
            case OpCode.Client.SET_UPDATE_SPEED:
                speed = self._read_int() / 100
                manager.ws_connection.update_speed = speed  # TODO
                await self.reply(
                    OpCode.Server.SET_UPDATE_SPEED, manager.ws_connection.protocol,
                    [speed * 100]
                )
            case OpCode.Client.ADD_PASSENGER:
                floor_i = self._read_int()
                floor_d = self._read_int()
                manager.add_passenger(floor_i, floor_d)
                await self.reply(
                    OpCode.Server.ADD_PASSENGER, manager.ws_connection.protocol,
                    [floor_i, floor_d]
                )
            case OpCode.Client.ADD_PASSENGERS:
                count = self._read_int()
                passengers = [(self._read_int(), self._read_int()) for _ in range(count)]
                manager.add_passengers(passengers)

                await self.reply(
                    OpCode.Server.ADD_PASSENGERS, manager.ws_connection.protocol,
                    [count, *sum(passengers, ())]
                    # flatten passengers
                )

            case OpCode.Client.SET_ALGORITHM:
                algorithm_id = self._read_int()
                algorithm_name = Algorithms(algorithm_id).name.replace('_', ' ')
                cls = manager.algorithms[algorithm_name]
                manager.set_algorithm(cls)

                await self.reply(
                    OpCode.Server.SET_ALGORITHM, manager.ws_connection.protocol,
                    [algorithm_id]
                )

            case OpCode.Client.SET_MAX_LOAD:
                max_load = self._read_int()
                manager.set_max_load(max_load)
                await self.reply(
                    OpCode.Server.SET_MAX_LOAD, manager.ws_connection.protocol,
                    [max_load]
                )

            case OpCode.Client.NEW_SIMULATION:
                manager.reset()
                # (int: floors, int: speed, int: max_load, strL algorithm, int: seed, int: simulation_speed, int: update_speed)
                await self.reply(OpCode.Server.NEW_SIMULATION, manager.ws_connection.protocol, [
                    manager.algorithm.floors,
                    manager.algorithm.max_load,
                    algo_to_enum(manager.algorithm.__class__),
                    manager.speed,
                    manager.ws_connection.update_speed
                ])
            case OpCode.Client.STOP_SIMULATION:
                manager.pause()
                await self.reply(OpCode.Server.STOP_SIMULATION, manager.ws_connection.protocol)

            case OpCode.Client.START_SIMULATION:
                manager.play()
                await self.reply(OpCode.Server.START_SIMULATION, manager.ws_connection.protocol)

    async def reply(self, opcode, connection, data: List[int] = None) -> None:
        """Replies to the client with a server packet"""
        await ServerPacket(opcode, data).send(connection)

    async def ack(self, connection) -> None:
        """Sends an ACK packet to the client"""
        await self.reply(OpCode.Server.ACK, connection)

    def __str__(self) -> str:
        """Returns a string representation of the packet"""
        integer_data = [str(b2i(self.raw_data[n:n+4])) for n in range(12, len(self.raw_data) - 8, 4)]
        return f'<ClientMessage command={self.command.name} data=[{", ".join(integer_data)}]>'


class ServerPacket:
    def __init__(
        self, command: OpCode.Server, data: List[int] = None
    ) -> None:
        """Creates a server packet"""
        self.command = command

        if data is not None:
            self.data = b''.join(map(i2b, data))
        else:
            self.data = b''

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

    async def send(self, connection):
        """Sends the packet to the client"""
        try:
            await connection.send(bytes(self))
        except ConnectionClosed:
            print('connection closed before message could be sent')
            pass
        else:
            logger.debug(f'Sent message to {connection.remote_address}: {self}')

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
        integer_data = [str(b2i(self.data[n:n+4])) for n in range(0, len(self.data), 4)]
        return f'<ServerMessage command={self.command.name} data=[{', '.join(integer_data)}]>'
    # convert 12th index onwards to integers
