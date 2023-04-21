import random
from dataclasses import dataclass, field
import statistics
from typing import List

from enums import Direction, LogLevel
from errors import BadArgument, FullElevator


@dataclass
class GeneratedStats:
    values: List[float | int] = field(default_factory=list)

    def append(self, value: float | int):
        self.values.append(value)

    @property
    def mean(self):
        if len(self.values) == 0:
            return 0
        return statistics.mean(self.values)

    @property
    def median(self):
        if len(self.values) == 0:
            return 0
        return statistics.median(self.values)

    @property
    def minimum(self):
        if len(self.values) == 0:
            return 0
        return min(self.values)

    @property
    def maximum(self):
        if len(self.values) == 0:
            return 0
        return max(self.values)

    def __str__(self):
        return f'{self.minimum:.2f}/{self.mean:.2f}/{self.median:.2f}/{self.maximum:.2f}'

    def __or__(self, other: 'GeneratedStats') -> 'CombinedStats':
        """Combine two GeneratedStats objects using the | operator"""
        if not isinstance(other, GeneratedStats):
            return super().__or__(other)

        return CombinedStats([self, other])

    def to_dict(self):
        return {
            'mean': self.mean,
            'median': self.median,
            'minimum': self.minimum,
            'maximum': self.maximum,
        }

@dataclass
class CombinedStats:
    stats: List[GeneratedStats | int] = field(default_factory=list)

    def append(self, stat: GeneratedStats):
        self.stats.append(stat)

    def extend(self, stats: List[GeneratedStats]):
        self.stats.extend(stats)

    @property
    def mean(self):
        if len(self.stats) == 0:
            return 0
        if isinstance(self.stats[0], int):
            return statistics.mean(self.stats)

        return statistics.mean([stat.mean for stat in self.stats])

    @property
    def median(self):
        if len(self.stats) == 0:
            return 0

        if isinstance(self.stats[0], int):
            return statistics.median(self.stats)

        return statistics.mean([stat.median for stat in self.stats])

    @property
    def minimum(self):
        if len(self.stats) == 0:
            return 0

        if isinstance(self.stats[0], int):
            return min(self.stats)

        return statistics.mean([stat.minimum for stat in self.stats])

    @property
    def maximum(self):
        if len(self.stats) == 0:
            return 0

        if isinstance(self.stats[0], int):
            return max(self.stats)

        return statistics.mean([stat.maximum for stat in self.stats])

    def __str__(self):
        return f'{self.minimum:.2f}/{self.mean:.2f}/{self.median:.2f}/{self.maximum:.2f}'

    def __or__(self, other: 'GeneratedStats') -> 'CombinedStats':
        """Combines another GeneratedStats object using the | operator"""
        if not isinstance(other, GeneratedStats):
            return super().__or__(other)

        return CombinedStats(self.stats + [other])

    def to_dict(self):
        return {
            'mean': self.mean,
            'median': self.median,
            'minimum': self.minimum,
            'maximum': self.maximum,
        }

@dataclass
class SimulationStats:
    ticks: int
    algorithm_name: str
    wait_time: GeneratedStats
    time_in_lift: GeneratedStats
    occupancy: GeneratedStats

    def __str__(self) -> str:
        fmt_text = f'Tick: {self.ticks}\nAlgorithm: {self.algorithm_name}\n\n(MIN/MEAN/MED/MAX)\n\n'
        fmt_text += f'Wait Time: {self.wait_time}\n'
        fmt_text += f'Time in Lift: {self.time_in_lift}\n'
        fmt_text += f'Occupancy: {self.occupancy}'
        return fmt_text


@dataclass
class LogMessage:
    """A log message object

    Attributes:
        level: LogLevel
            The level of the log message
        message: str
            The message to log
        tick: init
            The tick the message was logged
    """

    level: LogLevel
    message: str
    tick: int


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
        enter_lift_tick: int
    """

    id: int = field(init=False, default_factory=lambda: random.randint(0, 1000000))
    initial_floor: int
    destination_floor: int
    weight: int
    current_floor: int = field(init=False, default=None)
    elevator: "Elevator" = field(init=False, default=None, repr=False)
    tick_created: int = field(init=False, default=None, repr=False)
    enter_lift_time: int = field(init=False, default=None, repr=False)

    def __post_init__(self):
        self.current_floor = self.initial_floor

    def __repr__(self) -> str:
        return f'Load(id={self.id}, initial_floor={self.initial_floor}, destination_floor={self.destination_floor}, weight={self.weight} current_floor={self.current_floor} elevator={bool(self.elevator)})'

class ElevatorManager:
    """A global class that houses the elevators"""

    def __init__(self, parent, floors, *, elevators=None, loads=None) -> None:
        self.parent: 'TestSuite | wx.Window' = parent
        self.floors = floors
        self.elevators: List[Elevator] = elevators or []
        self.loads: List[Load] = loads or []
        self.max_load = 15 * 60

        self.tick_count = 0
        self.wait_times = GeneratedStats()
        self.time_in_lift = GeneratedStats()
        self.occupancy = GeneratedStats()

    @property
    def stats(self):
        return SimulationStats(
            ticks=self.tick_count,
            algorithm_name=self.name,
            wait_time=self.wait_times,
            time_in_lift=self.time_in_lift,
            occupancy=self.occupancy,
        )

    @property
    def pending_loads(self) -> List[Load]:
        return [load for load in self.loads if load.elevator is None]

    @property
    def simulation_running(self) -> bool:
        """Returns True if there are loads in the system"""
        return len(self.loads) > 0

    def get_new_destination(self, elevator):
        """Gets a new destination for an elevator

        elevator: Elevator
            The elevator to get a new destination for
        """
        raise NotImplementedError(
            "get_new_destination must be implemented in a subclass"
        )

    def pre_load_check(self, load, elevator):
        """Checks if a load is allowed to enter the elevator

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        return True

    def pre_unload_check(self, load, elevator):
        """Checks if a load is allowed to leave the elevator

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        return True

    def on_load_removed(self, load, elevator):
        """Runs after a load is unloaded

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        pass

    def pre_tick(self):
        """Runs at the start of every tick"""
        pass

    def post_tick(self):
        """Runs at the end of every tick"""
        self.tick_count += 1

    def on_load_added(self, load, elevator):
        """Runs when a load is added to an elevator

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        pass

    def create_elevator(self, current_floor=1, attributes=None):
        """Creates a new elevator

        current_floor: int[Optional]
            The current floor of the elevator
            Default: 1
        attributes: list[Optional]
            A list of attributes to pass to the elevator
        """
        new_id = 1
        if self.elevators:
            new_id = self.elevators[-1].id + 1
        elevator = Elevator(self.parent, new_id, current_floor, attributes)
        self.elevators.append(elevator)
        return elevator

    def remove_elevator(self, elevator_id):
        """Removes an elevator

        elevator: Elevator
            The elevator to remove
        """
        for elevator in self.elevators:
            if elevator.id == elevator_id:
                self.elevators.remove(elevator)
                return
        raise BadArgument(f"No elevator with id {elevator_id}")

    def add_passenger(self, initial, destination):
        """Adds a passenger

        initial: int
            The floor the passenger is on
        destination: int
            The floor the passenger wants to go to
        """
        load = Load(initial, destination, 60)
        load.tick_created = self.parent.current_tick
        self.loads.append(load)

    def cycle(self):
        """Runs a cycle of the elevator manager"""
        # Boarding
        self.pre_tick()
        for elevator in self.elevators:
            if elevator.load <= self.max_load:
                loads_to_add = []
                for load in self.loads:
                    # add to elevator
                    if (
                        load.elevator is None
                        and load.initial_floor == elevator.current_floor
                    ):
                        if (
                            elevator.load
                            + load.weight
                            + sum(x.weight for x in loads_to_add)
                        ) > self.max_load:
                            continue
                        if not self.pre_load_check(load, elevator):
                            self.parent.WriteToLog(
                                LogLevel.DEBUG,
                                f"Load {load.id} failed preload for elevator {elevator.id}",
                            )
                            continue

                        self.parent.WriteToLog(
                            LogLevel.INFO,
                            f"Load {load.id} added to elevator {elevator.id}",
                        )
                        loads_to_add.append(load)
                        load.elevator = elevator
                        load.enter_lift_tick = self.parent.current_tick
                        wait_time = self.tick_count - load.tick_created
                        self.wait_times.append(wait_time)
                        elevator.add_load(load)

            elevator.cycle()
        self.post_tick()

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["parent"]
        return state


class Elevator:
    def __init__(self, parent, elevator_id, current_floor=1, attributes=None) -> None:
        self.id = elevator_id
        self.parent = parent
        self._current_floor = current_floor
        self.loads: List[Load] = []
        self.attributes: List[str] = attributes or []
        self.enabled: bool = True

        self._destination: int = self.parent.manager.get_new_destination(self)

    @property
    def destination(self):
        if self._destination == self.current_floor or self._destination is None:
            self._destination = self.parent.manager.get_new_destination(self)

        return self._destination

    @property
    def direction(self):
        dest = self.destination
        if dest is None:
            return None
        if dest > self.current_floor:
            return Direction.UP
        if dest < self.current_floor:
            return Direction.DOWN

    @property
    def load(self):
        return sum(x.weight for x in self.loads)

    @property
    def current_floor(self):
        return self._current_floor

    @current_floor.setter
    def current_floor(self, value):
        return self._move(self.current_floor - value)

    def _move(self, increment):
        """Moves the elevator

        increment: int
            The number of floors to move the elevator by (-1 or 1)
        """
        if abs(increment) != 1:
            raise BadArgument("Elevator can only move by 1 floor at a time")

        self.parent.WriteToLog(
            LogLevel.TRACE,
            f"Elevator {self.id} moving {increment} floors from {self.current_floor} to {self.current_floor + increment}",
        )
        self._current_floor += increment

        to_remove = []
        for load in self.loads:
            load.current_floor = self.current_floor

            # unloading off elevator
            if (
                load.destination_floor == self.current_floor
                and self.parent.manager.pre_unload_check(load, self)
            ):
                self.parent.WriteToLog(
                    LogLevel.INFO, f"{load.id} unloaded from elevator {self.id}"
                )
                self.parent.manager.time_in_lift.append(
                    self.parent.current_tick - load.enter_lift_tick + 1
                )
                load.elevator = None
                to_remove.append(load)

        for load in to_remove:
            self.loads.remove(load)
            self.parent.manager.loads.remove(load)

            self.parent.manager.on_load_removed(load, self)

    def cycle(self):
        """Runs a cycle of the elevator"""
        if not self.enabled:
            return

        increment = 0
        if self.direction == Direction.UP:
            increment = 1
        elif self.direction == Direction.DOWN:
            increment = -1

        if increment != 0:
            self._move(increment)

        if self.destination is None:
            self._destination = self.parent.manager.get_new_destination(self)

    def add_load(self, load):
        """Adds new loads to the elevator.

        loads: list[Load]
            A list of loads to add to the elevator
        """
        # Take a person as 60kg on average
        if (
            self.parent.manager.max_load is not None
            and self.load + load.weight > self.parent.manager.max_load
        ):
            raise FullElevator(self.id)

        self.loads.append(load)
        self.parent.manager.on_load_added(load, self)

    def __repr__(self) -> str:
        return f"<Elevator {self.id} load={self.load // 60} destination={self.destination} current_floor={self._current_floor}>"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Elevator):
            return self.id == other.id
        return super().__eq__(other)

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["parent"]
        return state
