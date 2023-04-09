import random
from typing import List
from models import Direction, ElevatorManager, Elevator, Load


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
        self.attended_to = set()

    @property
    def pending_loads(self) -> List[Load]:
        return list(filter(lambda x: x.id not in self.attended_to, super().pending_loads))

    def _calculate_direction(self, elevator, destination_floor):
            if elevator.current_floor > destination_floor:
                self.current_direction[elevator.id] = Direction.DOWN
            else:
                self.current_direction[elevator.id] = Direction.UP

    def get_new_destination(self, elevator: Elevator):
        """Gets a new destination for an elevator using the random strategy

        elevator: Elevator
            The elevator to get a new destination for
        """
        if elevator.load != 0:
            # there is load, go to closest
            destination_floor = sorted(elevator.loads, key=lambda x: abs(x.destination_floor - elevator.current_floor))[0].destination_floor
        else:
            if len(self.pending_loads) == 0:
                # no pending loads
                self.current_direction[elevator.id] = None
                return None

            go_to = sorted(self.pending_loads, key=lambda x: x.tick_created)[0]
            self.attended_to.add(go_to.id)
            destination_floor = go_to.initial_floor

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

    def on_load_removed(self, load, elevator):
        if elevator.load == 0:
            # No more loads
            self.current_direction[elevator.id] = None
        if load.id in self.attended_to:
            self.attended_to.remove(load.id)

        return super().on_load_removed(load, elevator)

    def on_load_added(self, load, elevator):
        if len(elevator.loads) == 1:
            # First load, reset destination
            elevator._destination = self.get_new_destination(elevator)
        return super().on_load_added(load, elevator)


class ElevatorManagerKnuthDash(ElevatorManagerKnuth):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.dash_to_floor = None  # if not None, the elevator will dash to this floor

    def get_new_destination(self, elevator: Elevator):
        """Gets a new destination for an elevator using the random strategy

        elevator: Elevator
            The elevator to get a new destination for
        """
        destination_floor = super().get_new_destination(elevator)
        if elevator.load == 0:
            self.dash_to_floor = destination_floor

        return destination_floor

    def pre_load_check(self, load, elevator: Elevator):
        if self.dash_to_floor is not None and self.dash_to_floor != elevator.current_floor:
            return False

        return super().pre_load_check(load, elevator)

    def on_load_added(self, load, elevator):
        self.dash_to_floor = None
        return super().on_load_added(load, elevator)