from enum import IntEnum, Enum


class ID(IntEnum):
    PANEL_ELEVATORS = 110
    PANEL_DEBUG_CONTROL = 121
    PANEL_DEBUG_LOG = 122

    BUTTON_ADD_PASSENGER = 21
    BUTTON_CONTROL_PLAY = 22

    MENU_APP_EXIT = 310

    SELECT_ELEVATOR_ADD = 410
    SELECT_ELEVATOR_REMOVE = 411
    SELECT_PASSENGER_INITIAL = 420
    SELECT_PASSENGER_DESTINATION = 421


class Direction(IntEnum):
    UP = 1
    DOWN = -1


class LogLevel(IntEnum):
    TRACE = 1
    DEBUG = 2
    INFO = 3
    WARNING = 4
    ERROR = 5


class LogOrigin(Enum):
    SIMULATION = 1
    TEST = 2
    FILE_HANDLER = 3
    ERROR_HANDLER = 4


class ActionType(Enum):
    ADD_TICK = 1
    RUN_CYCLE = 2
    MOVE_ELEVATOR = 3
    LOAD_LOAD = 4
    UNLOAD_LOAD = 5


class Unicode:
    UP = '\u2191'
    DOWN = '\u2193'
    ARROW = '\u2192'


class Constants:
    DEFAULT_ALGORITHM = 'Destination Dispatch'
    DEFAULT_FLOORS = 10
    MAX_PROCESSES = 3
    MAX_NUM_LOADS_REMOVED_PER_TICK = 3


class _InfinitySentinel:
    def __str__(self) -> str:
        return 'Infinity'


Infinity = _InfinitySentinel()
