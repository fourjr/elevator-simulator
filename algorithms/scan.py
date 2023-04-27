from models import Direction, ElevatorAlgorithm, Elevator, Load
from typing import List


class ElevatorAlgorithmSCAN(ElevatorAlgorithm):
    """The standard elevator algorithm"""

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
        if elevator.current_floor > destination_floor:
            self.current_direction[elevator.id] = Direction.DOWN
        else:
            self.current_direction[elevator.id] = Direction.UP

    def get_new_destination(self, elevator: Elevator):
        """Gets a new destination for an elevator using the knuth strategy

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

            go_to = sorted(available_loads, key=lambda x: x.tick_created)[0]
            self.attended_to[elevator.id] = go_to.initial_floor
            destination_floor = go_to.initial_floor
            self.current_direction[elevator.id] = None

        if self.current_direction.get(elevator.id) is None:
            self._calculate_direction(elevator, destination_floor)

        return destination_floor

    def pre_load_check(self, load, elevator: Elevator):
        if elevator.current_floor == elevator.destination or elevator.destination is None:
            self.current_direction[elevator.id] = None

        if self.current_direction.get(elevator.id) is None:
            return True
        elif self.current_direction[elevator.id] == Direction.UP:
            if load.initial_floor < load.destination_floor:
                return True
        elif self.current_direction[elevator.id] == Direction.DOWN:
            if load.initial_floor > load.destination_floor:
                return True

        return False

    def on_load_load(self, load, elevator):
        if len(elevator.loads) == 1:
            # First load, reset destination
            elevator._destination = self.get_new_destination(elevator)

        return super().on_load_load(load, elevator)

    def on_elevator_move(self, elevator: Elevator):
        if elevator.current_floor == self.floors:
            self.current_direction[elevator.id] = Direction.DOWN
        elif elevator.current_floor == 0:
            self.current_direction[elevator.id] = Direction.UP

        if elevator.id in self.attended_to and elevator.current_floor == self.attended_to[elevator.id]:
            del self.attended_to[elevator.id]


__name__ = "SCAN"
__algorithm__ = ElevatorAlgorithmSCAN
