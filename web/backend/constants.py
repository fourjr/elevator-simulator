from enum import IntEnum


class PacketConstants:
    START_BYTES = b'\xE0\xEA\x0A\x08'
    END_BYTES = b'\xFF\xFF\xFF\xFF'


class OpCode:
    class Client(IntEnum):
        ADD_ELEVATOR = 0  # (int: current_floor)
        REMOVE_ELEVATOR = 1  # (int: elevator_id)
        SET_FLOORS = 2  # (int: floor_count)
        SET_SIMULATION_SPEED = 3  # (int: speed)
        ADD_PASSENGER = 4  # (int: initial, int: destination)
        ADD_PASSENGERS = 5  # (int: count, (int: initial, int: destination) * count)
        SET_ALGORITHM = 6  # TODO (int: algorithm_names)
        SET_MAX_LOAD = 7  # (int: new_max_load)
        STOP_SIMULATION = 8
        START_SIMULATION = 9
        NEW_SIMULATION = 10
        ADD_LOAD = 11  # (int: initial, int: destination)
        REMOVE_LOAD = 12  # (int: load_id)
        SET_UPDATE_SPEED = 13  # (int: update_speed)

    class Server(IntEnum):
        NEW_SIMULATION = 0
        ACK = 1
        CLOSE = 2
        GAME_UPDATE_STATE = 3
        ADD_ELEVATOR = 4
        REMOVE_ELEVATOR = 5
        SET_FLOORS = 6
        ADD_PASSENGER = 7
        ADD_PASSENGERS = 8
        GAME_STATE = 9
        ERROR = 10
        SET_SIMULATION_SPEED = 11
        SET_UPDATE_SPEED = 12
        SET_ALGORITHM = 13
        STOP_SIMULATION = 14
        START_SIMULATION = 15
        SET_MAX_LOAD = 16

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
