from dataclasses import dataclass, field
import itertools


@dataclass
class Load:
    """A load object

    Attributes:
        initial_floor: int
            The floor the load is on
        destination_floor: int
            The floor the load wants to go to
        weight: int
            The load in kg (human - 60)
        elevator: Optional[Elevator]
            Elevator the load is in
        tick_created: int
            Default: 0
        enter_lift_tick: int
    """

    _id_iter = itertools.count()

    id: int = field(init=False, default_factory=lambda: next(Load._id_iter))
    initial_floor: int
    destination_floor: int
    weight: int
    current_floor: int = field(init=False, default=None)
    elevator: 'Elevator' = field(init=False, default=None, repr=False)
    tick_created: int = field(init=False, default=0, repr=False)
    enter_lift_time: int = field(init=False, default=None, repr=False)

    def __post_init__(self):
        self.current_floor = self.initial_floor

    def __repr__(self) -> str:
        return f'Load(id={self.id}, initial_floor={self.initial_floor}, destination_floor={self.destination_floor}, weight={self.weight} current_floor={self.current_floor} elevator={bool(self.elevator)})'

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Load):
            return super().__eq__(other)
        return self.id == other.id

    def copy(self):
        load = Load(self.initial_floor, self.destination_floor, self.weight)
        load.current_floor = self.current_floor
        load.elevator = self.elevator
        load.tick_created = self.tick_created
        load.enter_lift_time = self.enter_lift_time
        return load
