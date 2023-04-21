import os
import queue
from datetime import datetime
from enum import IntEnum
import json
import multiprocessing
import random
from dataclasses import dataclass, field
import time
from typing import List, Tuple
from multiprocessing import Queue, JoinableQueue

from elevators import ElevatorManagerOverhead
from enums import LogLevel
from models import CombinedStats, Load, SimulationStats
from utils import Constants, load_algorithms


class LogOrigin(IntEnum):
    SIMULATION = 1
    TEST = 2


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

@dataclass
class TestSettings:
    name: str
    seed: int
    speed: int
    floors: int
    num_elevators: int
    num_passengers: int
    algorithm_name: str
    total_iterations: int
    loads: List[Load] = field(default_factory=list)

    def __post_init__(self):
        for _ in range(self.num_passengers):
            initial, destination = random.sample(range(1, self.floors + 1), 2)
            load = Load(initial, destination, 60)
            load.tick_created = 0
            self.loads.append(load)

    @property
    def algorithm(self):
        return self.suite.algorithms[self.algorithm_name]

    def to_dict(self):
        return {
            'name': self.name,
            'seed': self.seed,
            'speed': self.speed,
            'floors': self.floors,
            'num_elevators': self.num_elevators,
            'num_passengers': self.num_passengers,
            'total_iterations': self.total_iterations,
        }

class ElevatorManagerConsumer(ElevatorManagerOverhead):
    def __init__(
        self,
        p_count,
        in_queue, out_queue,
        parent
    ):
        self.p_count = p_count
        self.algorithms = load_algorithms()
        super().__init__(self, None, self.algorithms['Knuth'], gui=False, log_func=self.WriteToLog)
        self.process = multiprocessing.Process(target=self.go, args=(in_queue, out_queue), daemon=True)
        self._running = False

    @property
    def running(self):
        return self._running

    def go(self, in_queue, out_queue):
        while True:
            n_iter, settings = in_queue.get()

            random.seed((settings.seed + n_iter) % 2**32)
            algo = self.algorithms[settings.algorithm_name]
            algo.name = settings.algorithm_name
            self.reset(algo)

            self.set_speed(settings.speed)
            self.set_floors(settings.floors)

            for _ in range(settings.num_elevators):
                self.add_elevator(random.randint(1, settings.floors))
            self.manager.loads.extend(settings.loads)
            self.WriteToLog(LogLevel.INFO, f'{self.p_count=} START SIMULATION: {n_iter=} {settings.name=}', LogOrigin.TEST)
            self.active = True
            self.start_simulation()

            self.WriteToLog(LogLevel.INFO, f'{self.p_count=} END SIMULATION: {n_iter=} {settings.name=} {self.current_tick=}', LogOrigin.TEST)
            out_queue.put(((n_iter, settings), self.manager.stats))
            in_queue.task_done()

    def send_event(self):
        return

    def on_tick(self):
        if self._running is True and self.manager.simulation_running is False:
            self.end_simulation()

        # timeout
        if self.current_tick == 1000:
            # self.end_simulation()
            self.WriteToLog(LogLevel.INFO, f'{self.p_count=} TIMEOUT', LogOrigin.TEST)
            print(self.manager.loads)
            print(self.manager.pending_loads)
            print(self.manager.elevators)
            print(self.manager.attended_to)

    def start_simulation(self):
        self._running = True
        self.loop()

    def end_simulation(self):
        self._running = False

    def WriteToLog(self, level: LogLevel, message, origin=LogOrigin.SIMULATION):
        if (level not in (LogLevel.DEBUG, LogLevel.TRACE, LogLevel.INFO) or origin == LogOrigin.TEST) or self.current_tick == 1000:
        # if self.count == 3 and level not in (LogLevel.TRACE, LogLevel.DEBUG):
        #     if message == '193224 unloaded from elevator 7':
        #         print('crisis')
        #         print(self.manager.loads)
        #         print(self.manager.pending_loads)
        #         print(self.manager.elevators).
            print(level.name, message)

    def __getstate__(self):
        obj = self.__dict__.copy()
        del obj['process']
        return obj

class TestSuite:
    def __init__(self, tests, max_processes=None):
        self.tests: List[TestSettings] = tests
        self.in_queue: JoinableQueue[Tuple[int, TestSettings]] = JoinableQueue()
        self.out_queue: Queue[Tuple[Tuple[int, TestSettings], SimulationStats]] = Queue()

        hard_max_processes = min(multiprocessing.cpu_count(), sum(x.total_iterations for x in self.tests))
        if max_processes is None:
            self.max_processes = hard_max_processes
        else:
            self.max_processes = min(max_processes, hard_max_processes)

        for test in self.tests:
            for i in range(test.total_iterations):
                self.in_queue.put((i + 1, test))

        self.results: dict[TestSettings, TestStats] = {}

        self.processes = []

    def start(self):
        """Starts the Test Suite"""
        for count in range(self.max_processes):
            self.processes.append(ElevatorManagerConsumer(count, self.in_queue, self.out_queue, self))

        for p in self.processes:
            p.process.start()

        try:
            self.in_queue.join()
        except KeyboardInterrupt:
            return

        print('All tests finished, gathering results')
        while True:
            try:
                (count, settings), stats = self.out_queue.get(block=False)
            except queue.Empty:
                break
            else:
                if settings.name not in self.results:
                    self.results[settings.name] = (settings, TestStats())

                self.results[settings.name][1].append(stats)

        self.close_suite()

    def save_results(self):
        dt = datetime.now().isoformat().replace(':', '-')
        if not os.path.isdir('results'):
            os.mkdir('results')

        fn = f'results/{dt}.json'
        with open(fn, 'w') as f:
            json.dump([{**settings.to_dict(), 'stats': stats.to_dict()} for settings, stats in self.results.values()], f, indent=4)
        print(f'Saved results to {fn}')

    def close_suite(self):
        self.save_results()
        self.in_queue.close()
        self.out_queue.close()
