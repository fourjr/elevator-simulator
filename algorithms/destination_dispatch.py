import math
from typing import List
from models import ElevatorAlgorithm, Elevator, Load


class DestinationDispatch(ElevatorAlgorithm):
    """An algorithm that uses more advanced information
    This assumes that the manager knows the destination floor of each individual load

    The zone range of the elevator is defined by the first load it picks up.
    It is a ± floor range calculated by the load_floor_ratio

    1. Service the closest load
    2. Pick up any loads on the way whose destination floor is within the zone range of the elevator
    3. Repeat step 1 once we run out of loads
    """
    name = 'Destination Dispatch'

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.attended_to = {}

    @property
    def pending_loads(self) -> List[Load]:
        return list(filter(lambda x: x.id not in self.attended_to, super().pending_loads))

    @property
    def zone_range(self):
        lf_ratio = len(self.loads) / self.floors
        return math.ceil((1 / lf_ratio) * 20)

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
                return None
            # go to the nearest by initial floor
            go_to = sorted(
                available_loads,
                key=lambda x: abs(x.initial_floor - elevator.current_floor),
            )[0]

            self.attended_to[elevator.id] = go_to
            destination_floor = go_to.initial_floor

        return destination_floor

    def pre_load_check(self, load, elevator: Elevator):
        if elevator.id in self.attended_to:
            if self.attended_to[elevator.id] == load:
                return True
            if abs(self.attended_to[elevator.id].destination_floor - load.destination_floor) <= self.zone_range:
                return True

        return False

    def on_load_unload(self, load, elevator: Elevator):
        if len(elevator.loads) == 0 and elevator.id in self.attended_to:
            del self.attended_to[elevator.id]

    def on_load_load(self, load, elevator):
        if len(elevator.loads) == 1:
            # First load, reset destination
            elevator._destination = self.get_new_destination(elevator)


__algorithm__ = DestinationDispatch
