import random
from models import Direction, ElevatorManager, Elevator


class ElevatorManagerRandom(ElevatorManager):
    def get_new_destination(self, elevator: Elevator):
        """Gets a new destination for an elevator using the random strategy

        elevator: Elevator
            The elevator to get a new destination for
        """
        if len(elevator.loads) == 0:
            # elevator empty, try to get new load
            pending_loads = [load for load in self.loads if load.elevator is None]
            if len(pending_loads) == 0:
                return None
            load = random.choice(pending_loads)
            return load.initial_floor
        else:
            load = random.choice(elevator.loads)
            return load.destination_floor


class ElevatorManagerRolling(ElevatorManager):
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

        print('f')