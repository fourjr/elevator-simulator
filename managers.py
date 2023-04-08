import random
from models import ElevatorManager, Elevator


class ElevatorManagerRandom(ElevatorManager):
    def get_new_destination(self, elevator: Elevator):
        """Gets a new destination for an elevator using the random strategy

        elevator: Elevator
            The elevator to get a new destination for
        """
        if len(elevator.loads) == 0:
            return None
        load = random.choice(elevator.loads)
        return load['destination']
