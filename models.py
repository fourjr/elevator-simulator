from enum import IntEnum


class Direction(IntEnum):
    UP = 1
    DOWN = -1


class ElevatorError(Exception):
    pass


class FullElevator(ElevatorError):
    """Raised when an elevator is full and unable to add new load"""
    def __init__(self, elevator_id) -> None:
        super().__init__(f'{elevator_id} is full, unable to add new load')


class BadArgument(ElevatorError):
    """Raised when arguments provided are not of a valid type or format"""
    pass


class ElevatorRunError(ElevatorError):
    """Raised when the elevator is unable to run during an automated process"""
    pass


class ElevatorManager:
    """A global class that houses the elevators"""
    def __init__(self, floors) -> None:
        self.floors = floors
        self.elevators = []

    def get_new_destination(self, elevator):
        """Gets a new destination for an elevator

        elevator: Elevator
            The elevator to get a new destination for
        """
        raise NotImplementedError('get_new_destination must be implemented in a subclass')

    def create_elevator(self, current_floor=1, attributes=None):
        """Creates a new elevator

        current_floor: int[Optional]
            The current floor of the elevator
            Default: 1
        attributes: list[Optional]
            A list of attributes to pass to the elevator
        """
        elevator = Elevator(self, len(self.elevators) + 1, current_floor, attributes)
        self.elevators.append(elevator)
        return elevator

    def cycle(self):
        """Runs a cycle of the elevator manager"""
        for elevator in self.elevators:
            elevator.cycle()

class Elevator:
    def __init__(self, manager, elevator_id, current_floor=1, attributes=None) -> None:
        self.id = elevator_id
        self._current_floor = current_floor
        self.destination = None

        self.max_load = None  # readonly
        self.loads = []
        # [ { initial, destination, load }]

        self.attributes = attributes or []
        self.manager = manager
        self.enabled = True

    @property
    def direction(self):
        if self.destination is None:
            return None
        if self.destination > self.current_floor:
            return Direction.UP
        if self.destination < self.current_floor:
            return Direction.DOWN

    @property
    def load(self):
        return sum(x.load for x in self.loads)

    @property
    def current_floor(self):
        return self._current_floor
    
    @current_floor.setter
    def current_floor(self, value):
        return self.move(self.current_floor - value)

    def _move(self, increment):
        """Moves the elevator

        increment: int
            The number of floors to move the elevator by (-1 or 1)
        """
        if abs(increment) != 1:
            raise BadArgument('Elevator can only move by 1 floor at a time')

        self._current_floor += increment

        for load in self.loads:
            if load['destination'] == self.current_floor:
                self.loads.remove(load)

    def cycle(self):
        """Runs a cycle of the elevator"""
        if not self.enabled:
            return

        if self.destination is None:
            increment = 0
        if self.direction == Direction.UP:
            increment = 1
        elif self.direction == Direction.DOWN:
            increment = -1

        if increment > 0:
            self.move(increment)

        if self.destination is None:
            self.manager.get_new_destination(self)

    def add_load(self, loads):
        """Adds new loads to the elevator.
        Generally, a person is taken to be 60kg on average.

        loads: list[Load]
            A Load is a dictionary that contains general information
            about the load, the initial and destination floor.
            [ { initial, destination, load }, ... ]
        """
        # Take a person as 60kg on average
        new_load = sum(x.load for x in loads)
        if self.max_load is not None and self.load + new_load > self.max_load:
            raise FullElevator(self.id)

        self.loads.extend(loads)

    def __repr__(self) -> str:
        return f'<Elevator {self.id} load={self.load}>'

    def __eq__(self, other: object) -> bool:
        return self.id == other.id