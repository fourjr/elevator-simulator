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
            if len(self.pending_loads) == 0:
                return None
            load = random.choice(self.pending_loads)
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


class ElevatorManagerKnuth(ElevatorManager):
    """The standard elevator algorithm"""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_direction = {}

    def get_new_destination(self, elevator: Elevator):
        """Gets a new destination for an elevator using the random strategy

        elevator: Elevator
            The elevator to get a new destination for
        """
        if elevator.load != 0:
            # go to closest
            destination_floor = sorted(elevator.loads, key=lambda x: abs(x.destination_floor - elevator.current_floor))[0].destination_floor
        else:
            if len(self.pending_loads) == 0:
                # no pending loads
                self.current_direction[elevator.id] = None
                return None

            destination_floor = sorted(self.pending_loads, key=lambda x: x.tick_created)[0].initial_floor

        if self.current_direction.get(elevator.id) is None:
            if elevator.current_floor > destination_floor:
                self.current_direction[elevator.id] = Direction.DOWN
            else:
                self.current_direction[elevator.id] = Direction.UP

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

    def post_unload(self, load, elevator):
        if elevator.load == 0:
            # No more loads
            self.current_direction[elevator.id] = None
            # elevator._destination = None
