import copy
from dataclasses import InitVar, dataclass, field
from datetime import datetime
from enum import IntEnum
import random
from typing import List


class Direction(IntEnum):
    UP = 1
    DOWN = -1


class LogLevel(IntEnum):
    TRACE = 1
    DEBUG = 2
    INFO = 3
    WARNING = 4
    ERROR = 5

@dataclass
class LogMessage:
    """A log message object

    Attributes:
        level: LogLevel
            The level of the log message
        message: str
            The message to log
        tick: init
            The tick the message was logged
    """
    level: LogLevel
    message: str
    tick: int

class ElevatorError(Exception):
    pass


class FullElevator(ElevatorError):
    """Raised when an elevator is full and unable to add new load"""
    def __init__(self, elevator_id) -> None:
        super().__init__(f'{elevator_id} is full, unable to add new load')


class BadArgument(ElevatorError):
    """Raised when arguments provided are not of a valid type or format"""
    pass


class ElevatorRunError(ElevatorError):
    """Raised when the elevator is unable to run during an automated process"""
    pass


@dataclass
class Load:
    """A load object

    Attributes:
        initial_floor: int
            The floor the load is on
        destination_floor: int
            The floor the load wants to go to
        weight: int
            The load in kg (human - 60)
        elevator: Optional[Elevator]
            Elevator the load is in
        tick_created: int
        enter_lift_tick: int
    """
    id: int = field(init=False, default_factory=lambda: random.randint(0, 1000000))
    initial_floor: int
    destination_floor: int
    weight: int
    current_floor: int = field(init=False, default=None)
    elevator: 'Elevator' = field(init=False, default=None, repr=False)
    tick_created: int = field(init=False, default=None, repr=False)
    enter_lift_time: int = field(init=False, default=None, repr=False)

    def __post_init__(self):
        self.current_floor = self.initial_floor

class ElevatorManager:
    """A global class that houses the elevators"""
    def __init__(self, thread, floors, *, elevators=None, loads=None) -> None:
        self.thread = thread
        self.floors = floors
        self.elevators: List[Elevator] = elevators or []
        self.loads: List[Load] = loads or []
        self.max_load = 15 * 60

        self.wait_times = []
        self.time_in_lift = []
        self.occupancy = []
        self.name = self.__class__.__name__.replace("ElevatorManager", "")

    @property
    def pending_loads(self) -> List[Load]:
        return [load for load in self.loads if load.elevator is None]

    def get_new_destination(self, elevator):
        """Gets a new destination for an elevator

        elevator: Elevator
            The elevator to get a new destination for
        """
        raise NotImplementedError('get_new_destination must be implemented in a subclass')

    def pre_load_check(self, load, elevator):
        """Checks if a load is allowed to enter the elevator

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        return True

    def pre_unload_check(self, load, elevator):
        """Checks if a load is allowed to leave the elevator

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        return True

    def post_unload(self, load, elevator):
        """Runs after a load is unloaded

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        pass

    def create_elevator(self, current_floor=1, attributes=None):
        """Creates a new elevator

        current_floor: int[Optional]
            The current floor of the elevator
            Default: 1
        attributes: list[Optional]
            A list of attributes to pass to the elevator
        """
        new_id = 1
        if self.elevators:
            new_id = self.elevators[-1].id + 1
        elevator = Elevator(self.thread, new_id, current_floor, attributes)
        self.elevators.append(elevator)
        return elevator

    def add_passenger(self, initial, destination):
        """Adds a passenger

        initial: int
            The floor the passenger is on
        destination: int
            The floor the passenger wants to go to
        """
        load = Load(initial, destination, 60)
        load.tick_created = self.thread.current_tick
        self.loads.append(load)

    def cycle(self):
        """Runs a cycle of the elevator manager"""
        # Boarding
        for elevator in self.elevators:
            if elevator.load <= self.max_load:
                loads_to_add = []
                for load in self.loads:
                    # add to elevator
                    if load.elevator is None and load.initial_floor == elevator.current_floor:
                        if (elevator.load + load.weight + sum(x.weight for x in loads_to_add)) > self.max_load:
                            continue
                        if not self.pre_load_check(load, elevator):
                            self.thread.window.WriteToLog(LogLevel.DEBUG, f'Load {load.id} failed preload for elevator {elevator.id}')
                            continue

                        self.thread.window.WriteToLog(LogLevel.INFO, f'Load {load.id} added to elevator {elevator.id}')
                        loads_to_add.append(load)

                        load.elevator = elevator
                        load.enter_lift_tick = self.thread.current_tick
                        wait_time = self.thread.current_tick - load.tick_created
                        self.wait_times.append(wait_time)

                if loads_to_add:
                    elevator.add_loads(loads_to_add)

            elevator.cycle()

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['thread']
        return state

class Elevator:
    def __init__(self, thread, elevator_id, current_floor=1, attributes=None) -> None:
        self.id = elevator_id
        self._current_floor = current_floor
        self._destination: int = None

        self.loads: List[Load] = []

        self.attributes: List[str] = attributes or []
        self.thread = thread
        self.enabled: bool = True

    @property
    def destination(self):
        if self._destination == self.current_floor:
            self._destination = self.thread.manager.get_new_destination(self)

        return self._destination

    @property
    def direction(self):
        if self.destination is None:
            return None
        if self.destination > self.current_floor:
            return Direction.UP
        if self.destination < self.current_floor:
            return Direction.DOWN

    @property
    def load(self):
        return sum(x.weight for x in self.loads)

    @property
    def current_floor(self):
        return self._current_floor

    @current_floor.setter
    def current_floor(self, value):
        return self._move(self.current_floor - value)

    def _move(self, increment):
        """Moves the elevator

        increment: int
            The number of floors to move the elevator by (-1 or 1)
        """
        if abs(increment) != 1:
            raise BadArgument('Elevator can only move by 1 floor at a time')

        self.thread.window.WriteToLog(LogLevel.TRACE, f'Elevator {self.id} moving {increment} floors from {self.current_floor} to {self.current_floor + increment}')
        self._current_floor += increment

        to_remove = []
        for load in self.loads:
            load.current_floor = self.current_floor

            # unloading off elevator
            if load.destination_floor == self.current_floor and self.thread.manager.pre_unload_check(load, self):
                self.thread.window.WriteToLog(LogLevel.INFO, f'{load.id} unloaded from elevator {self.id}')
                self.thread.manager.time_in_lift.append(self.thread.current_tick - load.enter_lift_tick + 1)
                load.elevator = None
                to_remove.append(load)

        for load in to_remove:
            self.loads.remove(load)
            self.thread.manager.loads.remove(load)

            self.thread.manager.post_unload(load, self)

    def cycle(self):
        """Runs a cycle of the elevator"""
        if not self.enabled:
            return

        increment = 0
        if self.direction == Direction.UP:
            increment = 1
        elif self.direction == Direction.DOWN:
            increment = -1

        if increment != 0:
            self._move(increment)

        if self.destination is None:
            self._destination = self.thread.manager.get_new_destination(self)

    def add_loads(self, loads):
        """Adds new loads to the elevator.

        loads: list[Load]
            A list of loads to add to the elevator
        """
        # Take a person as 60kg on average
        new_load = sum(x.weight for x in loads)
        if self.thread.manager.max_load is not None and self.load + new_load > self.thread.manager.max_load:
            raise FullElevator(self.id)

        self.loads.extend(loads)

    def __repr__(self) -> str:
        return f'<Elevator {self.id} load={self.load}>'

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Elevator):
            return self.id == other.id
        return super().__eq__(other)

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['thread']
        return state
