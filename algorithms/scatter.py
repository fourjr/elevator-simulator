import random
from models import Elevator, ElevatorAlgorithm


class ElevatorAlgorithmScatter(ElevatorAlgorithm):
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



__name__ = "Scatter"
__algorithm__ = ElevatorAlgorithmScatter
