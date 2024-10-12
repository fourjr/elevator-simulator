from dataclasses import dataclass
from enum import IntEnum
from typing import Tuple


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
    SET_UPDATE_RATE = 11
    SET_MAX_LOAD = 12

    GAME_UPDATE_STATE = 13

    DASHBOARD = 20


class GameUpdateType(IntEnum):
    ELEVATOR_MOVE = 0
    ELEVATOR_DESTINATION = 1
    LOAD_UNLOAD = 2
    LOAD_LOAD = 3


@dataclass
class GameStateUpdate:
    update_type: GameUpdateType
    elevator_id: int
    parameter: int

    def flatten(self) -> Tuple[int]:
        return (int(self.update_type), self.elevator_id, self.parameter)


class Algorithms(IntEnum):
    Destination_Dispatch = 0
    FCFS = 1
    LOOK = 2
    NStepLOOK = 3
    Rolling = 4
    Scatter = 5
