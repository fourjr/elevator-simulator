from enum import IntEnum


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


class LogOrigin(IntEnum):
    SIMULATION = 1
    TEST = 2
