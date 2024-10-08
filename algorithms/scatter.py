from models import Elevator, ElevatorAlgorithm


class ElevatorAlgorithmScatter(ElevatorAlgorithm):
    """A scatter algorithm (randomised loads)

    1. Service a random load
    2. Pick up any loads on the way, indifferent of direction
    3. Repeat step 1 once we run out of loads
    """
    name = 'Scatter'

    def get_new_destination(self, elevator: Elevator):
        """Gets a new destination for an elevator

        elevator: Elevator
            The elevator to get a new destination for
        """
        if len(elevator.loads) == 0:
            # elevator empty, try to get new load
            if len(self.pending_loads) == 0:
                return None
            load = self.rnd.choice(self.pending_loads)
            return load.initial_floor
        else:
            load = self.rnd.choice(elevator.loads)
            return load.destination_floor


__algorithm__ = ElevatorAlgorithmScatter
