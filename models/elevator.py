import logging
from typing import List

from utils import ActionType, Constants, Direction, FullElevatorError
from models import ActionQueue, Action


class Elevator:
    def __init__(self, manager, elevator_id, current_floor=1) -> None:
        self.id = elevator_id
        self.manager: 'ElevatorManager' = manager
        self._current_floor = current_floor
        self.loads: List['Load'] = []
        self.enabled: bool = True
        self.action_manager = ActionQueue()

        self._destination: int = None
        self.destination = self.manager.algorithm.get_new_destination(self)

    def copy(self):
        """Creates a copy of the elevator"""
        ev = Elevator(self.manager, self.id, self.current_floor)
        ev._destination = self._destination
        ev.enabled = self.enabled
        ev.loads = [load.copy() for load in self.loads]
        ev.action_manager = self.action_manager.copy()
        return ev

    @property
    def destination(self):
        if self._destination is None:
            self.destination = self.manager.algorithm.get_new_destination(self)

        return self._destination

    @destination.setter
    def destination(self, value):
        self.manager.on_elevator_destination_change(self, value)
        self._destination = value

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
            logging.DEBUG,
            f'Elevator {self.id} moving {increment} floors from {self.current_floor} to {self.current_floor + increment}',
        )
        self._current_floor += increment

    def loop(self):
        if not self.enabled:
            return

        while True:
            # keep running until we reach an add tick
            action = self.action_manager.get()
            match action.action_type:
                case ActionType.ADD_TICK:
                    return
                case ActionType.LOAD_LOAD:
                    load = action.argument
                    self.load_load(load)
                case ActionType.UNLOAD_LOAD:
                    load = action.argument
                    self.unload_load(load)
                case ActionType.RUN_CYCLE:
                    self.cycle()
                case ActionType.MOVE_ELEVATOR:
                    self.move_elevator()
                case _:
                    raise NotImplementedError(f'Unknown action type {action.action_type}')

    def move_elevator(self):
        increment = 0
        if self.direction == Direction.UP:
            increment = 1
        elif self.direction == Direction.DOWN:
            increment = -1

        if increment != 0:
            self._move(increment)
            self.manager.algorithm.on_elevator_move(self)

            for load in self.loads:
                load.current_floor = self.current_floor
                self.manager.on_load_move(load)

        if self._destination == self.current_floor or self._destination is None:
            self.destination = self.manager.algorithm.get_new_destination(self)

        self.manager.on_elevator_move(self)

    def cycle(self):
        """Runs a cycle of the elevator"""
        load_change_count = 0

        # remove loads
        for load in self.loads:
            # unloading off elevator
            if load.destination_floor != self.current_floor or not self.manager.algorithm.pre_unload_check(
                load, self
            ):
                continue

            if load_change_count == 0:
                self.action_manager.open_door()

            self.action_manager.add(Action(ActionType.UNLOAD_LOAD, load))
            load_change_count += 1
            if load_change_count % Constants.MAX_NUM_LOADS_REMOVED_PER_TICK == 0:
                self.action_manager.tick()

        # add loads
        added_loads = 0
        if self.load <= self.manager.algorithm.max_load:
            for load in self.manager.algorithm.loads:
                # add to elevator
                if (
                    load.elevator is not None
                    or load.initial_floor != self.current_floor
                    or self.load + added_loads + load.weight > self.manager.algorithm.max_load
                    or not self.manager.algorithm.pre_load_check(load, self)
                ):
                    continue

                if load_change_count == 0:
                    self.action_manager.open_door()

                load.elevator = True  # mark elevator as taken

                self.action_manager.add(Action(ActionType.LOAD_LOAD, load))
                added_loads += load.weight
                load_change_count += 1
                if load_change_count % Constants.MAX_NUM_LOADS_REMOVED_PER_TICK == 0:
                    self.action_manager.tick()

        if load_change_count % 3 != 0:
            self.action_manager.tick()

        if load_change_count > 0:
            self.action_manager.close_door()

        # move elevator
        self.action_manager.tick(3)
        self.action_manager.add(Action(ActionType.MOVE_ELEVATOR))

    def load_load(self, load):
        """Adds new loads to the elevator.

        load: Load
            A load to add to the elevator
        """
        # Take a person as 60kg on average
        if (
            self.manager.algorithm.max_load is not None
            and self.load + load.weight > self.manager.algorithm.max_load
        ):
            raise FullElevatorError(self.id)

        self.manager.WriteToLog(logging.DEBUG, f'Load {load.id} added to elevator {self.id}')
        load.enter_lift_tick = self.manager.algorithm.tick_count
        wait_time = self.manager.algorithm.tick_count - load.tick_created
        self.manager.algorithm.wait_times.append(wait_time)

        load.elevator = self
        self.loads.append(load)
        self.manager.on_load_load(load, self)
        self.manager.algorithm.on_load_load(load, self)

    def unload_load(self, load):
        """Removes loads from the elevator.

        load: Load
            A load to remove from the elevator
        """
        self.manager.WriteToLog(logging.DEBUG, f'Load {load.id} unloaded from elevator {self.id}')
        self.manager.algorithm.time_in_lift.append(self.manager.algorithm.tick_count - load.enter_lift_tick + 1)

        load.elevator = None
        self.loads.remove(load)
        self.manager.on_load_unload(load, self)
        self.manager.algorithm.on_load_unload(load, self)
        self.manager.algorithm.remove_load(load)

    def __repr__(self) -> str:
        if getattr(self, 'manager', None):
            return f'<Elevator {self.id} load={self.load} destination={self.destination} current_floor={self._current_floor}>'
        else:
            return f'<Elevator* {self.id} load={self.load} current_floor={self._current_floor}>'

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Elevator):
            return self.id == other.id
        return super().__eq__(other)

    def __getstate__(self):
        state = self.__dict__.copy()
        if 'manager' in state:
            del state['manager']
        return state
