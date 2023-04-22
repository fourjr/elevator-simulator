import random
from models import Direction, ElevatorAlgorithm, Elevator, Load


class ElevatorAlgorithmRolling(ElevatorAlgorithm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.prev_direction = {}

    def get_new_destination(self, elevator: Elevator):
        """Gets a new destination for an elevator using the random strategy

        elevator: Elevator
            The elevator to get a new destination for
        """
        prev_direction = self.prev_direction.get(elevator.id, None)
        if prev_direction is None:
            prev_direction = random.choice([Direction.UP, Direction.DOWN])

        if prev_direction is Direction.DOWN:
            self.prev_direction[elevator.id] = Direction.UP
            return self.floors
        else:
            self.prev_direction[elevator.id] = Direction.DOWN
            return 1



__name__ = "Rolling"
__algorithm__ = ElevatorAlgorithmRolling
