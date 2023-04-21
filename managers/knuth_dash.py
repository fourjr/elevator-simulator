from managers.knuth import ElevatorManagerKnuth
from models import Elevator


class ElevatorManagerKnuthDash(ElevatorManagerKnuth):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.dash_to_floor = {}

    def get_new_destination(self, elevator: Elevator):
        """Gets a new destination for an elevator using the random strategy

        elevator: Elevator
            The elevator to get a new destination for
        """
        if self.dash_to_floor.get(elevator.id):
            return self.dash_to_floor[elevator.id]

        destination_floor = super().get_new_destination(elevator)
        if elevator.load == 0:
            self.dash_to_floor[elevator.id] = destination_floor

        return destination_floor

    def pre_load_check(self, load, elevator: Elevator):
        if self.dash_to_floor.get(elevator.id) is not None and self.dash_to_floor.get(elevator.id) != elevator.current_floor:
            return False

        return super().pre_load_check(load, elevator)

    def on_load_added(self, load, elevator):
        return super().on_load_added(load, elevator)

    def post_tick(self):
        for elevator in self.elevators:
            if elevator.id in self.dash_to_floor and elevator.current_floor == self.dash_to_floor[elevator.id]:
                del self.dash_to_floor[elevator.id]

        return super().post_tick()

__name__ = "Knuth Dash"
__manager__ = ElevatorManagerKnuthDash
