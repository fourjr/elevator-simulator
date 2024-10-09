from enum import IntEnum


class PacketConstants:
    START_BYTES = b'\xE0\xEA\x0A\x08'
    END_BYTES = b'\xFF\xFF\xFF\xFF'


class OpCode(IntEnum):
    CLOSE = 0
    ERROR = 1

    NEW_SIMULATION = 2
    START_SIMULATION = 3
    STOP_SIMULATION = 4

    ADD_ELEVATOR = 5
    REMOVE_ELEVATOR = 6
    ADD_PASSENGERS = 7
    SET_FLOORS = 8
    SET_ALGORITHM = 9
    SET_SIMULATION_SPEED = 10
    SET_UPDATE_SPEED = 11
    SET_MAX_LOAD = 12

    GAME_UPDATE_STATE = 13

    DASHBOARD = 20


class GameUpdate(IntEnum):
    MOVE_LOAD = 8
    SET_ALGORITHM = 6
    SET_MAX_LOAD = 7


class LogUpdate(IntEnum):
    INFO = 0
    WARNING = 1
    ERROR = 2


class Algorithms(IntEnum):
    Destination_Dispatch = 0
    FCFS = 1
    LOOK = 2
    NStepLOOK = 3
    Rolling = 4
    Scatter = 5


class CloseReason:
    UNEXPECTED = 0
    SERVER_CLOSE = 1
    CLIENT_CLOSE = 2
    NO_MANAGER = 3


class ErrorCode:
    BAD_ARGUMENT = 0
    UNEXPECTED_ERROR = 1
