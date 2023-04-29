from models import ElevatorAlgorithm, Elevator


class ElevatorAlgorithmFCFS(ElevatorAlgorithm):
    """The standard elevator algorithm"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.attending_to = {}

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
            try:
                go_to = self.pending_loads[0]  # get the first in the queue
            except IndexError:
                # no pending loads
                return None

            self.attending_to[elevator.id] = go_to.initial_floor
            destination_floor = go_to.initial_floor

        return destination_floor

    def pre_load_check(self, load, elevator: Elevator):
        if elevator.id in self.attending_to and self.attending_to[elevator.id] == load.initial_floor:
            return True

        return False

    def on_load_load(self, load, elevator):
        if len(elevator.loads) == 1:
            # First load, reset destination
            elevator._destination = self.get_new_destination(elevator)

        super().on_load_load(load, elevator)


__name__ = 'FCFS'
__algorithm__ = ElevatorAlgorithmFCFS
