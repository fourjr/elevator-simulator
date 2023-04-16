import copy
from datetime import datetime
from enum import IntEnum
import json
import random
from dataclasses import dataclass, field
from typing import Callable, List

from elevators import ElevatorManagerThread
from enums import LogLevel
from models import CombinedStats, ElevatorManager, Load, SimulationStats
from utils import Constants, load_algorithms


class LogOrigin(IntEnum):
    SIMULATION = 1
    TEST = 2


# Figure out threading.Event
# Right now, each SIM is one thread
# Have to properly integrate it

@dataclass
class TestStats:
    ticks: CombinedStats = field(default_factory=CombinedStats)
    wait_time: CombinedStats = field(default_factory=CombinedStats)
    time_in_lift: CombinedStats = field(default_factory=CombinedStats)
    occupancy: CombinedStats = field(default_factory=CombinedStats)

    def append(self, stats: SimulationStats):
        self.ticks.append(stats.ticks)
        self.wait_time.append(stats.wait_time)
        self.time_in_lift.append(stats.time_in_lift)
        self.occupancy.append(stats.occupancy)

    def to_dict(self):
        return {
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
            }
        }


class ElevatorManagerThreadTestWrapper(ElevatorManagerThread):
    def __init__(self, parent, manager: ElevatorManager, *args, **kwargs):
        super().__init__(parent, manager, *args, event=None gui=False, **kwargs)
        self.test: 'Test' = parent
        self.simulation_running = False

    def send_event(self):
        return

    def on_tick(self):
        super().on_tick()
        if self.simulation_running is True and self.manager.simulation_running is False:
            self.test.on_raw_end_simulation()

class Test:
    suite: 'TestSuite'

    def __init__(self, name, repeat, *args, **kwargs):
        self.name = name
        self.suite = None  # will be added by the suite
        self.time_started = None

        self.current_iteration = 0
        self.total_iterations = repeat
        self.manager_thread = None

        self.seed = kwargs.pop('seed', random.randint(0, 2**32 - 1))
        self.speed = kwargs.pop("speed", 100)
        self.floors = kwargs.pop("floors", 10)
        self.num_elevators = kwargs.pop("num_elevators", 1)
        self.num_passengers = kwargs.pop("num_passengers", 0)
        self.algorithm_name = kwargs.pop("algorithm_name", Constants.DEFAULT_ALGORITHM)

        self.loads = kwargs.pop("loads", None)
        self.stats = TestStats()

        self.args = args
        self.kwargs = kwargs

    @property
    def algorithm(self):
        return self.suite.algorithms[self.algorithm_name]

    def on_raw_end_simulation(self):
        self.end_simulation()

    def start_test(self):
        random.seed(self.seed)
        self.time_started = datetime.now()
        self.start_simulation()
        self.on_test_start()

    def on_test_start(self):
        print('Test started:', self)

    def end_test(self):
        self.on_test_end()
        self.suite.on_test_end()

    def on_test_end(self):
        print('Test ended:', self)
        print('-------------------')

    def start_simulation(self):
        thread = ElevatorManagerThreadTestWrapper(self, self.algorithm)
        thread.pause()
        thread.set_speed(self.speed)
        thread.set_floors(self.floors)
        thread.set_algorithm(self.algorithm_name)
        for _ in range(self.num_elevators):
            self.add_elevator(random.randint(1, self.floors))

        passengers = []
        for _ in range(self.num_passengers):
            passengers.append(random.sample(range(1, self.manager_thread.manager.floors + 1), 2))

        thread.add_passengers(passengers)
        thread.add_random_passengers(self.num_passengers)
        if self.loads is not None:
            thread.manager.loads.extend(self.loads)

        self.current_iteration += 1
        thread.play()
        self.on_simulation_start()

    def on_simulation_start(self):
        print('Simulation started:', self.current_iteration)

    def end_simulation(self):
        # play the next
        self.pause()
        simulation_stats: SimulationStats = self.suite.get_stats()
        self.stats.append(simulation_stats)

        if self.current_iteration < self.total_iterations:
            self.start_simulation()
        else:
            self.end_test()

        self.on_simulation_end()

    def on_simulation_end(self):
        print('Simulation ended:', self.current_iteration)

    def to_dict(self):
        return {
            'name': self.name,
            'time_started': self.time_started.isoformat(),
            'seed': self.seed,
            'speed': self.speed,
            'floors': self.floors,
            'num_elevators': self.num_elevators,
            'num_passengers': self.num_passengers,
            'current_iteration': self.current_iteration,
            'total_iterations': self.total_iterations,
            'stats': self.stats.to_dict(),
        }

    def __repr__(self) -> str:
        return f'Test({self.name})'

    def add_random_passengers(self, count: int):
        if not self.running:
            raise RuntimeError("Test suite not started")

        passengers = []
        for _ in range(count):
            passengers.append(random.sample(range(1, self.manager_thread.manager.floors + 1), 2))

        self.manager_thread.add_passengers(passengers)

    # region
    def pause(self):
        if not self.running:
            raise RuntimeError("Test suite not started")

        if self.manager_thread.active:
            self.manager_thread.set_active(False)
        else:
            print("Test not running")

    def play(self):
        if not self.running:
            raise RuntimeError("Test suite not started")

        if not self.manager_thread.active:
            self.manager_thread.set_active(True)
        else:
            raise RuntimeError("Test already running")

    # endregion
class TestSuite:
    def __init__(self, tests):
        self.tests: List[Test] = tests

        for test in self.tests:
            test.suite = self

        self.iter_tests = iter(self.tests)
        self.current_test = None

        self.manager_thread = None
        self.manager = None

        self.algorithms = load_algorithms()
        self.current_algorithm = self.algorithms[Constants.DEFAULT_ALGORITHM]

    @property
    def running(self):
        return self.manager_thread is not None and self.manager_thread.is_open

    def run_next_test(self):
        try:
            self.current_test = next(self.iter_tests)
        except StopIteration:
            self.current_test = None
            self.close_suite()
        else:
            self.current_test.start_test()

    def start(self):
        """Starts the Test Suite"""
        self.manager_thread = ElevatorManagerThread(self, self.on_raw_update_manager, self.current_algorithm, gui=False)
        self.manager = copy.deepcopy(self.manager_thread.manager)
        self.pause()
        self.run_next_test()

    def on_raw_update_manager(self, **event):
        manager = event.pop('manager')
        old_manager = self.manager
        self.manager = copy.deepcopy(manager)
        if self.running:
            self.on_update_manager(old_manager, manager)

    def on_update_manager(self, before: ElevatorManager, after: ElevatorManager):
        if self.current_test is not None:
            self.current_test.on_update_manager(before, after)

    def get_stats(self) -> SimulationStats:
        return self.manager_thread.manager.stats

    def on_test_end(self):
        self.run_next_test()

    def save_results(self):
        dt = datetime.now().isoformat().replace(':', '-')
        fn = f'results_{dt}.json'
        with open(fn, 'w') as f:
            json.dump([test.to_dict() for test in self.tests], f, indent=4)

    def close_suite(self):
        self.save_results()
        self.manager_thread.close()
        # self.manager_thread.join()

    def WriteToLog(self, level: LogLevel, message, origin=LogOrigin.SIMULATION):
        if level not in (LogLevel.DEBUG, LogLevel.TRACE, LogLevel.INFO):
            print(level.name, message)
