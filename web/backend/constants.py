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
        RESET = 8
        PAUSE = 9
        RESUME = 10
        REGISTER = 11
        ADD_LOAD = 12  # (int: initial, int: destination, weight: int)
        REMOVE_LOAD = 13  # (int: load_id)
        SET_UPDATE_SPEED = 15  # (int: update_speed)

    class Server(IntEnum):
        REGISTER = 0
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

    class GameUpdate(IntEnum):
        MOVE_LOAD = 8
        SET_ALGORITHM = 6
        SET_MAX_LOAD = 7

    class LogUpdate(IntEnum):
        INFO = 0
        WARNING = 1
        ERROR = 2


class Algorithms(IntEnum):
    DESTINATION_DISPATCH = 0
    FCFS = 1
    LOOK = 2
    NSTEPLOOK = 3
    ROLLING = 4
    SCATTER = 5


class CloseReason:
    UNEXPECTED = 0
    SERVER_CLOSE = 1
    CLIENT_CLOSE = 2
    NO_MANAGER = 3


class ErrorCode:
    BAD_ARGUMENT = 0
