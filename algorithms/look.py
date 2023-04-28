from algorithms.scan import ElevatorAlgorithmSCAN
from models import Elevator


class ElevatorAlgorithmLOOK(ElevatorAlgorithmSCAN):
    """The standard elevator algorithm"""

    def on_load_unload(self, load, elevator):
        if elevator.load == 0:
            # No more loads
            self.current_direction[elevator.id] = None

        return super().on_load_unload(load, elevator)

    def on_elevator_move(self, elevator: Elevator):
        if elevator.id in self.attended_to and elevator.current_floor == self.attended_to[elevator.id]:
            del self.attended_to[elevator.id]


__name__ = "LOOK"
__algorithm__ = ElevatorAlgorithmLOOK
