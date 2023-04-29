from algorithms.look import ElevatorAlgorithmLOOK
from constants import Direction
from models import Elevator
from utils import split_array


class ElevatorAlgorithmNStepLOOK(ElevatorAlgorithmLOOK):
    """The N-Step LOOK elevator algorithm

    Each elevator is assigned a unique zone of floors.

    1. Service the closest load whose initial floor is within the zone
    2. Pick up any loads on the way, travelling the same direction and in the zone
    3. Reverse direction upon reaching the top or bottom
    4. Repeat step 1 once we run out of loads
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.num_zones = len(self.elevators)
        self.zones = self.calculate_zones()

    def calculate_zones(self):
        if len(self.elevators) == 0:
            return []
        self.zones = list(split_array(list(range(1, self.floors + 1)), len(self.elevators)))
        # update elevators
        for ev in self.elevators:
            elevator_index = self.elevators.index(ev)
            ev.current_floor = self.zones[elevator_index][0]

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
            if elevator not in self.elevators:
                return None

            elevator_index = self.elevators.index(elevator)
            available_loads = list(
                filter(
                    lambda x: x.initial_floor in self.zones[elevator_index],
                    self.pending_loads,
                )
            )
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
        elevator_index = self.elevators.index(elevator)
        return load.initial_floor in self.zones[elevator_index] and super().pre_load_check(load, elevator)

    def on_elevator_added(self, elevator: Elevator):
        self.calculate_zones()

    def on_elevator_removed(self, elevator_id: int):
        self.calculate_zones()

    def on_floors_changed(self):
        self.calculate_zones()

    def on_elevator_move(self, elevator: Elevator):
        elevator_index = self.elevators.index(elevator)
        if elevator.current_floor == self.zones[elevator_index][-1]:  # last floor
            self.current_direction[elevator.id] = Direction.DOWN
        elif elevator.current_floor == self.zones[elevator_index][0]:  # first floor
            self.current_direction[elevator.id] = Direction.UP


__name__ = 'NStepLOOK'
__algorithm__ = ElevatorAlgorithmNStepLOOK
