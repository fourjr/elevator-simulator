from algorithms.scan import ElevatorAlgorithmSCAN
from models import Elevator, Load


class ElevatorAlgorithmLOOK(ElevatorAlgorithmSCAN):
    """The standard elevator algorithm"""

    def on_load_unload(self, load, elevator):
        if elevator.load == 0:
            # No more loads
            self.current_direction[elevator.id] = None

        return super().on_load_unload(load, elevator)


__name__ = 'LOOK'
__algorithm__ = ElevatorAlgorithmLOOK
