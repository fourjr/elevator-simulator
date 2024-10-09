import websockets


class ElevatorError(Exception):
    pass


class FullElevatorError(ElevatorError):
    """Raised when an elevator is full and unable to add new load"""

    def __init__(self, elevator_id) -> None:
        super().__init__(f'{elevator_id} is full, unable to add new load')
        self.elevator_id = elevator_id


class BadArgumentError(ElevatorError):
    """Raised when arguments provided are not of a valid type or format"""

    pass


class ElevatorRunError(ElevatorError):
    """Raised when the elevator is unable to run during an automated process"""

    pass


class InvalidAlgorithmError(ElevatorError):
    """Raised when the algorithm is not of a valid type"""

    pass


class TestTimeoutError(ElevatorError):
    """Raised when a test times out"""

    def __init__(self, process_name, n_iter, settings) -> None:
        super().__init__(process_name, n_iter, settings)
        self.process_name = process_name
        self.n_iter = n_iter
        self.settings = settings


class PacketError(ValueError):
    pass


class InvalidStartBytesError(PacketError):
    pass


class IncompletePacketError(PacketError):
    pass


class InvalidChecksumError(PacketError):
    pass


class NoManagerError(ElevatorError):
    pass
