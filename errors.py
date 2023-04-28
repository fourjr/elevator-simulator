class ElevatorError(Exception):
    pass


class FullElevator(ElevatorError):
    """Raised when an elevator is full and unable to add new load"""

    def __init__(self, elevator_id) -> None:
        super().__init__(f"{elevator_id} is full, unable to add new load")
        self.elevator_id = elevator_id


class BadArgument(ElevatorError):
    """Raised when arguments provided are not of a valid type or format"""

    pass


class ElevatorRunError(ElevatorError):
    """Raised when the elevator is unable to run during an automated process"""

    pass


class InvalidAlgorithm(ElevatorError):
    """Raised when the algorithm is not of a valid type"""

    pass


class TestTimeout(ElevatorError):
    """Raised when a test times out"""

    def __init__(self, process_name, n_iter, settings) -> None:
        super().__init__(process_name, n_iter, settings)
        self.process_name = process_name
        self.n_iter = n_iter
        self.settings = settings
