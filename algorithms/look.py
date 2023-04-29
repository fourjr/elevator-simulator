from typing import List

from constants import Direction
from models import ElevatorAlgorithm, Elevator, Load


class ElevatorAlgorithmLOOK(ElevatorAlgorithm):
    """The standard elevator algorithm

    1. Service the closest load
    2. Pick up any loads on the way, travelling the same direction
    3. Reverse direction upon reaching the top or bottom
    4. Repeat step 1 once we run out of loads
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_direction = {}
        self.attended_to = {}

    @property
    def pending_loads(self) -> List[Load]:
        return list(
            filter(
                lambda x: x.initial_floor not in self.attended_to.values(),
                super().pending_loads,
            )
        )

    def _calculate_direction(self, elevator, destination_floor):
        if destination_floor is None:
            self.current_direction[elevator.id] = None
        if elevator.current_floor > destination_floor:
            self.current_direction[elevator.id] = Direction.DOWN
        else:
            self.current_direction[elevator.id] = Direction.UP

    def get_new_destination(self, elevator: Elevator):
        """Gets a new destination for an elevator

        elevator: Elevator
            The elevator to get a new destination for
        """
        if elevator.load != 0:
            # there is load, go to closest
            destination_floor = sorted(
                elevator.loads,
                key=lambda x: abs(x.destination_floor - elevator.current_floor),
            )[0].destination_floor
        else:
            available_loads = self.pending_loads
            if len(available_loads) == 0:
                # no pending loads
                self.current_direction[elevator.id] = None
                return None

            go_to = sorted(available_loads, key=lambda x: abs(x.initial_floor - x.current_floor))[0]
            destination_floor = self.attended_to[elevator.id] = go_to.initial_floor
            self.current_direction[elevator.id] = None

        if self.current_direction.get(elevator.id) is None:
            self._calculate_direction(elevator, destination_floor)

        return destination_floor

    def pre_load_check(self, load, elevator: Elevator):
        if elevator.current_floor == elevator.destination or elevator.destination is None:
            self.current_direction[elevator.id] = None

        if self.current_direction.get(elevator.id) is None:
            return True

        if len(elevator.loads) == 0:
            # no load, direction does not matter
            return True

        if load.initial_floor > load.destination_floor:
            load_direction = Direction.DOWN
        else:
            load_direction = Direction.UP

        curr_direction = self.current_direction[elevator.id]
        if load_direction == curr_direction:
            return True

        return False

    def on_elevator_move(self, elevator: Elevator):
        if elevator.current_floor == self.floors:
            self.current_direction[elevator.id] = Direction.DOWN
        elif elevator.current_floor == 0:
            self.current_direction[elevator.id] = Direction.UP

    def on_load_load(self, load: Load, elevator: Elevator):
        if len(elevator.loads) == 1:
            # First load, reset destination
            elevator._destination = self.get_new_destination(elevator)

        if elevator.current_floor in self.attended_to.values():
            for k in self.attended_to:
                if self.attended_to[k] == elevator.current_floor:
                    del self.attended_to[k]
                    break
        if elevator.id in self.attended_to:
            del self.attended_to[elevator.id]

        return super().on_load_load(load, elevator)

    def on_load_unload(self, load, elevator):
        if len(elevator.loads) == 0:
            self.current_direction[elevator.id] = None

        return super().on_load_unload(load, elevator)


__name__ = 'LOOK'
__algorithm__ = ElevatorAlgorithmLOOK
