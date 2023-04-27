import itertools
import statistics
import threading
import time
import wx
from dataclasses import dataclass, field
from typing import Callable, List, Tuple

from enums import Direction, LogLevel, Constants
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
        return (
            f"{self.minimum:.2f}/{self.mean:.2f}/{self.median:.2f}/{self.maximum:.2f}"
        )

    def to_dict(self):
        return {
            "mean": self.mean,
            "median": self.median,
            "minimum": self.minimum,
            "maximum": self.maximum,
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
        return (
            f"{self.minimum:.2f}/{self.mean:.2f}/{self.median:.2f}/{self.maximum:.2f}"
        )

    def __or__(self, other: "GeneratedStats") -> "CombinedStats":
        """Combines another GeneratedStats object using the | operator"""
        if not isinstance(other, GeneratedStats):
            return super().__or__(other)

        return CombinedStats(self.stats + [other])

    def __len__(self):
        return len(self.stats)

    def to_dict(self):
        return {
            "mean": self.mean,
            "median": self.median,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }


@dataclass
class SimulationStats:
    ticks: int
    algorithm_name: str
    wait_time: GeneratedStats
    time_in_lift: GeneratedStats
    occupancy: GeneratedStats

    def __str__(self) -> str:
        fmt_text = f"Tick: {self.ticks}\nAlgorithm: {self.algorithm_name}\n\n(MIN/MEAN/MED/MAX)\n\n"
        fmt_text += f"Wait Time: {self.wait_time}\n"
        fmt_text += f"Time in Lift: {self.time_in_lift}\n"
        fmt_text += f"Occupancy: {self.occupancy}"
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
            Default: 0
        enter_lift_tick: int
    """

    _id_iter = itertools.count()

    id: int = field(init=False, default_factory=lambda: next(Load._id_iter))
    initial_floor: int
    destination_floor: int
    weight: int
    current_floor: int = field(init=False, default=None)
    elevator: "Elevator" = field(init=False, default=None, repr=False)
    tick_created: int = field(init=False, default=0, repr=False)
    enter_lift_time: int = field(init=False, default=None, repr=False)

    def __post_init__(self):
        self.current_floor = self.initial_floor

    def __repr__(self) -> str:
        return f"Load(id={self.id}, initial_floor={self.initial_floor}, destination_floor={self.destination_floor}, weight={self.weight} current_floor={self.current_floor} elevator={bool(self.elevator)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Load):
            return super().__eq__(other)
        return self.id == other.id


class ElevatorAlgorithm:
    """A global class that houses the elevators"""

    def __init__(self, manager, floors=None, *, elevators=None, loads=None) -> None:
        self.manager = manager
        self._floors = floors if floors is not None else Constants.DEFAULT_FLOORS
        self.elevators: List[Elevator] = elevators or []
        self.loads: List[Load] = loads or []
        self.max_load = 15 * 60

        self.tick_count = 0
        self.wait_times = GeneratedStats()
        self.time_in_lift = GeneratedStats()
        self.occupancy = GeneratedStats()

    @property
    def floors(self):
        return self._floors

    @floors.setter
    def floors(self, value):
        self._floors = value
        self.on_floors_changed()

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

    def pre_tick(self):
        """Runs at the start of every tick"""
        pass

    def post_tick(self):
        """Runs at the end of every tick"""
        self.tick_count += 1

    def on_load_load(self, load, elevator):
        """Runs when a load is added to an elevator

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        pass

    def on_load_unload(self, load, elevator):
        """Runs after a load is unloaded

        load: Load
            The load to check
        elevator: Elevator
            The elevator to check
        """
        pass

    def on_elevator_move(self, elevator):
        """Runs when an elevator moves

        elevator: Elevator
            The elevator that moved
        """
        pass

    def on_elevator_added(self, elevator):
        """Runs when an elevator is added

        elevator: Elevator
            The elevator that was added
        """
        pass

    def on_elevator_removed(self, elevator):
        """Runs when an elevator is removed

        elevator: Elevator
            The elevator that was removed
        """
        pass

    def on_floors_changed(self):
        """Runs when the number of floors is changed"""
        pass

    def on_load_added(self, load):
        """Runs when a load is added

        load: Load
            The load that was added
        """
        pass

    def on_load_removed(self, load):
        """Runs when a load is removed

        load: Load
            The load that was removed
        """
        pass

    def add_load(self, load):
        """Adds a load to the system
        
        load: Load
            The load to add"""
        self.loads.append(load)
        self.on_load_added(load)

    def remove_load(self, load):
        """Removes a load from the system
        
        load: Load
            The load to remove
        """
        self.loads.remove(load)
        self.on_load_removed(load)

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
        elevator = Elevator(self.manager, new_id, current_floor, attributes)
        self.elevators.append(elevator)
        self.on_elevator_added(elevator)
        return elevator

    def remove_elevator(self, elevator_id):
        """Removes an elevator

        elevator: Elevator
            The elevator to remove
        """
        for elevator in self.elevators:
            if elevator.id == elevator_id:
                self.elevators.remove(elevator)
                self.on_elevator_removed(elevator_id)
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
        load.tick_created = self.manager.current_tick
        self.add_load(load)

    def cycle(self):
        """Runs a cycle of the elevator algorithm"""
        # Boarding
        self.pre_tick()
        for elevator in self.elevators:
            if elevator.load <= self.max_load:
                loads_to_add = []
                for load in self.loads:
                    # add to elevator
                    if load.elevator is None and load.initial_floor == elevator.current_floor:
                        if elevator.load + load.weight + sum(x.weight for x in loads_to_add) > self.max_load:
                            continue
                        if not self.pre_load_check(load, elevator):
                            self.manager.WriteToLog(
                                LogLevel.DEBUG,
                                f"Load {load.id} failed preload for elevator {elevator.id}",
                            )
                            continue

                        self.manager.WriteToLog(
                            LogLevel.INFO,
                            f"Load {load.id} added to elevator {elevator.id}",
                        )
                        loads_to_add.append(load)
                        load.elevator = elevator
                        load.enter_lift_tick = self.manager.current_tick
                        wait_time = self.tick_count - load.tick_created
                        self.wait_times.append(wait_time)
                        elevator.add_load(load)

            elevator.cycle()
        self.post_tick()

    def __getstate__(self):
        state = self.__dict__.copy()
        if "manager" in state:
            del state["manager"]
        return state


class Elevator:
    def __init__(self, manager, elevator_id, current_floor=1, attributes=None) -> None:
        self.id = elevator_id
        self.manager: ElevatorManager = manager
        self._current_floor = current_floor
        self.loads: List[Load] = []
        self.attributes: List[str] = attributes or []
        self.enabled: bool = True

        self._destination: int = self.manager.algorithm.get_new_destination(self)

    @property
    def destination(self):
        if self._destination is None:
            self._destination = self.manager.algorithm.get_new_destination(self)

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
        return self._move(value - self.current_floor)

    def _move(self, increment):
        """Moves the elevator

        increment: int
            The number of floors to move the elevator by (-1 or 1)
        """
        self.manager.WriteToLog(
            LogLevel.TRACE,
            f"Elevator {self.id} moving {increment} floors from {self.current_floor} to {self.current_floor + increment}",
        )
        self._current_floor += increment

        to_remove = []
        for load in self.loads:
            load.current_floor = self.current_floor
            self.manager.on_load_move(load)

            # unloading off elevator
            if load.destination_floor == self.current_floor and self.manager.algorithm.pre_unload_check(load, self):
                self.manager.WriteToLog(
                    LogLevel.INFO, f"{load.id} unloaded from elevator {self.id}"
                )
                self.manager.algorithm.time_in_lift.append(
                    self.manager.current_tick - load.enter_lift_tick + 1
                )
                load.elevator = None
                to_remove.append(load)

        for load in to_remove:
            self.loads.remove(load)
            self.manager.algorithm.remove_load(load)

            self.manager.algorithm.on_load_unload(load, self)

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
            self.manager.algorithm.on_elevator_move(self)

        if self._destination == self.current_floor or self._destination is None:
            self._destination = self.manager.algorithm.get_new_destination(self)

    def add_load(self, load):
        """Adds new loads to the elevator.

        loads: list[Load]
            A list of loads to add to the elevator
        """
        # Take a person as 60kg on average
        if  self.manager.algorithm.max_load is not None and self.load + load.weight > self.manager.algorithm.max_load:
            raise FullElevator(self.id)

        self.loads.append(load)
        self.manager.algorithm.on_load_load(load, self)

    def __repr__(self) -> str:
        if getattr(self, 'manager', None):
            return f"<Elevator {self.id} load={self.load // 60} destination={self.destination} current_floor={self._current_floor}>"
        else:
            return f"<Elevator* {self.id} load={self.load // 60} current_floor={self._current_floor}>"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Elevator):
            return self.id == other.id
        return super().__eq__(other)

    def __getstate__(self):
        state = self.__dict__.copy()
        if "manager" in state:
            del state["manager"]
        return state


class ElevatorManager:
    def __init__(
        self,
        parent,
        event: Callable,
        algorithm: ElevatorAlgorithm,
        *,
        gui: bool = True,
        log_func: Callable = None,
    ):
        super().__init__()
        self.parent = parent
        self.event = event
        self.speed = 3
        self.algorithm: ElevatorAlgorithm = algorithm(self)
        self.active = False
        self.is_open = True
        self.current_tick = 0
        self.gui = gui

        if log_func is None:
            self.WriteToLog = self.parent.WriteToLog
        else:
            self.WriteToLog = log_func

    @property
    def running(self):
        raise NotImplementedError

    def on_tick(self):
        pass

    def loop(self):
        while self.running and self.is_open:
            if self.active:
                self.algorithm.cycle()
                self.current_tick += 1
                self.send_event()
                self.on_tick()

                if self.algorithm.simulation_running:
                    # only append if there are things going on
                    for elevator in self.algorithm.elevators:
                        self.algorithm.occupancy.append(
                            (elevator.load / self.algorithm.max_load) * 100
                        )

            time.sleep(3 * (1 / self.speed))

            # speed: 3 seconds per floor (1x)

    def send_event(self):
        if self.gui is True:
            event = self.event(algorithm=self.algorithm, thread=self)
            wx.PostEvent(self.parent, event)

    def add_elevator(self, current_floor: int, attributes=None):
        self.algorithm.create_elevator(current_floor, attributes)
        self.send_event()

    def remove_elevator(self, elevator_id: str):
        self.algorithm.remove_elevator(elevator_id)
        self.send_event()

    def set_floors(self, floor_count: int):
        self.algorithm.floors = floor_count
        self.send_event()

    def set_speed(self, speed: int):
        self.speed = speed

    def close(self):
        self.is_open = False

    def add_passenger(self, initial: int, destination: int):
        self.algorithm.add_passenger(initial, destination)
        self.send_event()

    def add_passengers(self, passengers: List[Tuple[int, int]]):
        for initial, destination in passengers:
            self.algorithm.add_passenger(initial, destination)
        self.send_event()

    def set_algorithm(self, cls: ElevatorAlgorithm):
        self.algorithm = cls(
            self,
            self.algorithm.floors,
            elevators=self.algorithm.elevators,
            loads=self.algorithm.loads,
        )
        self.send_event()

    def set_max_load(self, new_max_load: int):
        self.algorithm.max_load = new_max_load
        self.send_event()

    def reset(self, cls: ElevatorAlgorithm):
        self.current_tick = 0
        self.algorithm = cls(self)
        self.send_event()

    def set_active(self, active: bool):
        self.active = active

    def pause(self):
        self.set_active(False)

    def play(self):
        self.set_active(True)

    def on_load_move(self, load: Load):
        pass


class ElevatorManagerThread(ElevatorManager, threading.Thread):
    def __init__(
        self, parent, event: Callable, algorithm: ElevatorAlgorithm, *, gui: bool = True
    ):
        ElevatorManager.__init__(self, parent, event, algorithm, gui=gui)
        threading.Thread.__init__(self)
        self.start()

    def run(self):
        self.loop()

    @property
    def running(self):
        return self.is_alive()
