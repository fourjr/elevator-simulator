class ElevatorError(Exception):
    pass


class FullElevator(ElevatorError):
    """Raised when an elevator is full and unable to add new load"""

    def __init__(self, elevator_id) -> None:
        super().__init__(f"{elevator_id} is full, unable to add new load")


class BadArgument(ElevatorError):
    """Raised when arguments provided are not of a valid type or format"""
    pass


class ElevatorRunError(ElevatorError):
    """Raised when the elevator is unable to run during an automated process"""
    pass


class InvalidManager(ElevatorError):
    """Raised when the manager is not of a valid type"""
    pass
