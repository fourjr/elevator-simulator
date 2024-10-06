from enum import IntEnum


class Constants:
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
        SET_SEED = 14  # (int: seed)
        SET_UPDATE_SPEED = 15  # (int: update_speed)

    class Server(IntEnum):
        REGISTER = 0
        ACK = 1
        CLOSE = 2
        GAME_UPDATE_STATE = 3

    class GameUpdate(IntEnum):
        ADD_ELEVATOR = 0
        REMOVE_ELEVATOR = 1
        SET_FLOORS = 2
        MOVE_LOAD = 8
        ADD_PASSENGER = 4
        ADD_PASSENGERS = 5
        SET_ALGORITHM = 6
        SET_MAX_LOAD = 7

    class LogUpdate(IntEnum):
        INFO = 0
        WARNING = 1
        ERROR = 2


class CloseReason:
    UNEXPECTED = 0
    SERVER_CLOSE = 1
    CLIENT_CLOSE = 2
    NO_MANAGERS = 3
