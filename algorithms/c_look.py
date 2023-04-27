from collections import defaultdict
from algorithms.look import ElevatorAlgorithmLOOK
from enums import Direction


class ElevatorAlgorithmC_LOOK(ElevatorAlgorithmLOOK):
    """The C-LOOK elevator algorithm"""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_direction = defaultdict(self.get_initial_direction)

    def get_initial_direction(self):
        return Direction.UP


__name__ = "C-LOOK"
__algorithm__ = ElevatorAlgorithmC_LOOK
