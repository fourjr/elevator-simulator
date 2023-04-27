from collections import defaultdict
from algorithms.scan import ElevatorAlgorithmSCAN
from enums import Direction


class ElevatorAlgorithmC_SCAN(ElevatorAlgorithmSCAN):
    """The C-SCAN elevator algorithm"""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.current_direction = defaultdict(self.get_initial_direction)

    def get_initial_direction(self):
        return Direction.UP


__name__ = "C-SCAN"
__algorithm__ = ElevatorAlgorithmC_SCAN
