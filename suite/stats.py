import random
from dataclasses import dataclass, field
from typing import List

from constants import Infinity
from models import CombinedStats, Load
from models.stats import SimulationStats


@dataclass
class TestStats:
    ticks: CombinedStats = field(default_factory=CombinedStats)
    wait_time: CombinedStats = field(default_factory=CombinedStats)
    time_in_lift: CombinedStats = field(default_factory=CombinedStats)
    occupancy: CombinedStats = field(default_factory=CombinedStats)

    def __len__(self):
        assert len(self.ticks) == len(self.wait_time) == len(self.time_in_lift) == len(self.occupancy)

        return len(self.ticks)

    def append(self, stats: SimulationStats):
        self.ticks.append(stats.ticks)
        self.wait_time.append(stats.wait_time)
        self.time_in_lift.append(stats.time_in_lift)
        self.occupancy.append(stats.occupancy)

    def to_dict(self, include_raw_stats=True):
        data = {
            'aggregated': {
                'ticks': self.ticks.to_dict(),
                'wait_time': self.wait_time.to_dict(),
                'time_in_lift': self.time_in_lift.to_dict(),
                'occupancy': self.occupancy.to_dict(),
            },
            'raw': {
                'ticks': self.ticks.stats,
                'wait_time': [x.to_dict() for x in self.wait_time.stats],
                'time_in_lift': [x.to_dict() for x in self.time_in_lift.stats],
                'occupancy': [x.to_dict() for x in self.occupancy.stats],
            },
        }
        if not include_raw_stats:
            data.pop('raw')
        return data

    def __repr__(self) -> str:
        return f'<TestStats size={len(self)}>'


@dataclass
class TestSettings:
    """Settings for a single test

    name: str
        Name of the test
    seed: int
        Seed for the random number generator
    speed: Optional[int | Infinity]
        Speed of the simulation in relative ticks # TODO: improve explanation
        Default: Infinity
    floors: int
        Number of floors in the building
    num_elevators: int
        Number of elevators in the building
    num_passengers: int
        Number of passengers in the building (60kg loads)
    algorithm_name: str
        Name of the algorithm to use
    total_iterations: int
        Number of iterations to run the test for
    max_load: int
        Maximum load of the elevators (in kg)
    loads: Optional[List[Load]]
        List of custom loads to use
    init_func: Optional[Callable[[ElevatorAlgorithm], None]
        Function to call to initialize the algorithm
    on_tick: Optional[Callable[[ElevatorAlgorithm], None]
        Function to call every tick
    """

    id: int = field(init=False)
    name: str
    seed: int
    floors: int
    num_elevators: int
    num_passengers: int
    algorithm_name: str
    total_iterations: int
    max_load: int
    speed: int | Infinity = Infinity
    loads: List[Load] = field(default_factory=list)
    init_function: callable = None
    on_tick: callable = None

    def __post_init__(self):
        self.id = hash((self.name, self.algorithm_name, self.seed))

    def init_passengers(self, rnd: random.Random):
        for _ in range(self.num_passengers):
            initial, destination = rnd.sample(range(1, self.floors + 1), 2)
            load = Load(initial, destination, 60)
            self.loads.append(load)

    @property
    def algorithm(self):
        return self.suite.algorithms[self.algorithm_name]

    def to_dict(self, iteration_count=None):
        return {
            'name': self.name,
            'algorithm_name': self.algorithm_name,
            'seed': self.seed,
            'speed': self.speed if self.speed != Infinity else 'Infinity',
            'floors': self.floors,
            'num_elevators': self.num_elevators,
            'num_loads': len(self.loads),
            'total_iterations': iteration_count or self.total_iterations,
        }

    def __hash__(self) -> int:
        return hash(self.id)
