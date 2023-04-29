from typing import List

from constants import Direction, LogLevel
from errors import FullElevator


class Elevator:
    def __init__(self, manager, elevator_id, current_floor=1, attributes=None) -> None:
        self.id = elevator_id
        self.manager: 'ElevatorManager' = manager
        self._current_floor = current_floor
        self.loads: List['Load'] = []
        self.attributes: List[str] = attributes or []
        self.enabled: bool = True

        self._destination: int = self.manager.algorithm.get_new_destination(self)

    @property
    def destination(self):
        if self._destination is None:
            self._destination = self.manager.algorithm.get_new_destination(self)

        return self._destination

    @property
    def direction(self):
        dest = self.destination
        if dest is None:
            return None
        if dest > self.current_floor:
            return Direction.UP
        if dest < self.current_floor:
            return Direction.DOWN

    @property
    def load(self):
        return sum(x.weight for x in self.loads)

    @property
    def current_floor(self):
        return self._current_floor

    @current_floor.setter
    def current_floor(self, value):
        return self._move(value - self.current_floor)

    def _move(self, increment):
        """Moves the elevator

        increment: int
            The number of floors to move the elevator by (-1 or 1)
        """
        self.manager.WriteToLog(
            LogLevel.TRACE,
            f'Elevator {self.id} moving {increment} floors from {self.current_floor} to {self.current_floor + increment}',
        )
        self._current_floor += increment

        to_remove = []
        for load in self.loads:
            load.current_floor = self.current_floor
            self.manager.on_load_move(load)

            # unloading off elevator
            if load.destination_floor == self.current_floor and self.manager.algorithm.pre_unload_check(
                load, self
            ):
                self.manager.WriteToLog(LogLevel.TRACE, f'Load {load.id} unloaded from elevator {self.id}')
                self.manager.algorithm.time_in_lift.append(
                    self.manager.algorithm.tick_count - load.enter_lift_tick + 1
                )
                load.elevator = None
                to_remove.append(load)

        for load in to_remove:
            self.loads.remove(load)
            self.manager.algorithm.remove_load(load)

            self.manager.algorithm.on_load_unload(load, self)

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
            self.manager.algorithm.on_elevator_move(self)

        if self._destination == self.current_floor or self._destination is None:
            self._destination = self.manager.algorithm.get_new_destination(self)

    def add_load(self, load):
        """Adds new loads to the elevator.

        loads: list[Load]
            A list of loads to add to the elevator
        """
        # Take a person as 60kg on average
        if (
            self.manager.algorithm.max_load is not None
            and self.load + load.weight > self.manager.algorithm.max_load
        ):
            raise FullElevator(self.id)

        self.loads.append(load)
        self.manager.algorithm.on_load_load(load, self)

    def __repr__(self) -> str:
        if getattr(self, 'manager', None):
            return f'<Elevator {self.id} load={self.load // 60} destination={self.destination} current_floor={self._current_floor}>'
        else:
            return f'<Elevator* {self.id} load={self.load // 60} current_floor={self._current_floor}>'

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Elevator):
            return self.id == other.id
        return super().__eq__(other)

    def __getstate__(self):
        state = self.__dict__.copy()
        if 'manager' in state:
            del state['manager']
        return state
