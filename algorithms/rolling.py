from constants import Direction
from models import ElevatorAlgorithm, Elevator, Load


class ElevatorAlgorithmRolling(ElevatorAlgorithm):
    """A rolling elevator algorithm

    1. Pick a random direction to start with
    2. Pick up any loads on the way, travelling the same direction
    3. Reverse direction upon reaching the top or bottom
    4. Repeat step 1 once we run out of loads
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.curr_direction = {}

    def _get_curr_direction(self, elevator: Elevator):
        curr_direction = self.curr_direction.get(elevator.id, None)
        if curr_direction is None:
            curr_direction = self.rnd.choice([Direction.UP, Direction.DOWN])
            self.curr_direction[curr_direction] = curr_direction
        return curr_direction

    def get_new_destination(self, elevator: Elevator):
        """Gets a new destination for an elevator

        elevator: Elevator
            The elevator to get a new destination for
        """
        if len(self.pending_loads) == 0:
            return None

        curr_direction = self._get_curr_direction(elevator)
        if curr_direction is Direction.DOWN:
            return 1
        else:
            return self.floors

    def pre_load_check(self, load: Load, elevator):
        if load.initial_floor > load.destination_floor:
            load_direction = Direction.DOWN
        else:
            load_direction = Direction.UP

        curr_direction = self._get_curr_direction(elevator)
        if load_direction == curr_direction:
            return True

        return False

    def on_elevator_move(self, elevator):
        if elevator.current_floor == self.floors:
            self.curr_direction[elevator.id] = Direction.DOWN
            elevator._destination = self.get_new_destination(elevator)
        elif elevator.current_floor == 1:
            self.curr_direction[elevator.id] = Direction.UP
            elevator._destination = self.get_new_destination(elevator)


__name__ = 'Rolling'
__algorithm__ = ElevatorAlgorithmRolling
