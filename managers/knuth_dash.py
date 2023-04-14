from managers.knuth import ElevatorManagerKnuth
from models import Elevator


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


__name__ = "Knuth Dash"
__manager__ = ElevatorManagerKnuthDash
