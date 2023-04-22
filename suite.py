import os
import queue
import json
import multiprocessing as mp
import random
from datetime import datetime
from dataclasses import dataclass, field
import traceback
from typing import List, Tuple
from multiprocessing import Queue, JoinableQueue

from enums import LogLevel, LogOrigin
from errors import TestTimeout
from models import CombinedStats, Load, SimulationStats, ElevatorManager
from utils import load_algorithms


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

    def to_dict(self, include_raw=True):
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
            }
        }
        if not include_raw:
            data.pop('raw')
        return data


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


class TestSuiteConsumer(ElevatorManager):
    def __init__(
        self,
        in_queue, out_queue, error_queue
    ):
        self.algorithms = load_algorithms()
        super().__init__(self, None, self.algorithms['Knuth'], gui=False, log_func=self.log_message)
        self._running = False
        self._process = mp.Process(target=self.process_loop, args=(in_queue, out_queue, error_queue), daemon=True)
        self.name = self._process.name
        self.latest_load_move = 0
        self.previous_loads = []
        self.current_simulation = None

    @property
    def running(self):
        return self._running

    def start(self):
        self._process.start()

    def process_loop(self, in_queue, out_queue, error_queue):
        try:
            while True:
                n_iter, settings = in_queue.get()
                self.current_simulation = (n_iter, settings)

                random.seed((settings.seed + n_iter) % 2**32)
                algo = self.algorithms[settings.algorithm_name]
                algo.name = settings.algorithm_name
                self.reset(algo)

                self.set_speed(settings.speed)
                self.set_floors(settings.floors)

                for _ in range(settings.num_elevators):
                    self.add_elevator(random.randint(1, settings.floors))
                self.algorithm.loads.extend(settings.loads)

                self.active = True
                self.log_message(LogLevel.INFO, f'{self.name} START SIMULATION: {n_iter=} {settings.name=}', LogOrigin.TEST)

                try:
                    self.start_simulation()
                except TestTimeout as e:
                    # continue with next simulation
                    self.log_message(LogLevel.WARNING, f'{self.name} SKIP SIMULATION (TIMEOUT): {n_iter=} {settings.name=} {self.current_tick=}', LogOrigin.TEST)
                else:
                    self.log_message(LogLevel.INFO, f'{self.name} END SIMULATION: {n_iter=} {settings.name=} {self.current_tick=}', LogOrigin.TEST)
                    out_queue.put(((n_iter, settings), self.algorithm.stats))

                in_queue.task_done()

        except KeyboardInterrupt:
            return
        except Exception as e:
            if self.current_simulation is not None:
                n_iter, settings = self.current_simulation
                self.log_message(LogLevel.ERROR, f'{self.name} ERROR SIMULATION: {n_iter=} {settings.name=} {self.current_tick=}', LogOrigin.TEST)
            else:
                self.log_message(LogLevel.ERROR, f'{self.name} ERROR SIMULATION: {self.current_tick=}', LogOrigin.TEST)

            error_queue.put((self.name, e))

    def on_tick(self):
        if self._running is True and self.algorithm.simulation_running is False:
            self.end_simulation()

        # frozen loads
        if self.current_tick - self.latest_load_move > 500:
            self.end_simulation()
            n_iter, settings = self.current_simulation
            self.log_message(LogLevel.ERROR, f'{self.name=} TIMEOUT: {n_iter=} {settings.name=}', LogOrigin.TEST)
            raise TestTimeout(self.name, n_iter, settings)

    def on_load_move(self, _):
        self.latest_load_move = self.current_tick

    def start_simulation(self):
        self._running = True
        self.loop()

    def end_simulation(self):
        self._running = False

    def log_message(self, level: LogLevel, message, origin=LogOrigin.SIMULATION):
        if (level not in (LogLevel.DEBUG, LogLevel.TRACE, LogLevel.INFO) or origin == LogOrigin.TEST):
            print(level.name, message)

    def __getstate__(self):
        obj = self.__dict__.copy()
        del obj['_process']
        return obj


class ErrorProcess(mp.Process):
    def __init__(self, in_queue, out_queue, error_queue, consumers: List[TestSuiteConsumer], close_event):
        super().__init__(target=self.process_loop, args=(in_queue, out_queue, error_queue, consumers, close_event))

    def process_loop(self, in_queue, out_queue, error_queue, consumers, close_event):
        while close_event.is_set() is False:
            try:
                name, e = error_queue.get(timeout=1)
            except queue.Empty:
                continue

            del consumers[name]
            consumer = TestSuiteConsumer(in_queue, out_queue, error_queue)
            consumer.start()
            consumers[consumer.name] = consumer

            print(f'[E_HANDLER] INFO {name} died, restarting as {consumer.name}')
            traceback.print_exception(type(e), e, e.__traceback__)

            error_queue.task_done()


class TestSuite:
    def __init__(self, tests, max_processes=None, *, include_raw=True):
        self.tests: List[TestSettings] = tests
        self.in_queue: JoinableQueue[Tuple[int, TestSettings]] = JoinableQueue()
        self.out_queue: Queue[Tuple[Tuple[int, TestSettings], SimulationStats]] = Queue()
        self.error_queue: JoinableQueue[Tuple[str, Exception]] = JoinableQueue()
        self.close_event = mp.Event()
        self.include_raw = include_raw

        hard_max_processes = min(mp.cpu_count() - 1, sum(x.total_iterations for x in self.tests))
        if max_processes is None:
            self.max_processes = hard_max_processes
        else:
            self.max_processes = min(max_processes, hard_max_processes)

        for test in self.tests:
            for i in range(test.total_iterations):
                self.in_queue.put((i + 1, test))

        self.results: dict[TestSettings, TestStats] = {}

        self.consumers = {}
        self.error_process = None

    def start(self):
        """Starts the Test Suite"""
        for _ in range(self.max_processes):
            consumer = TestSuiteConsumer(self.in_queue, self.out_queue, self.error_queue)
            self.consumers[consumer.name] = consumer

        for p in self.consumers.values():
            p.start()

        self.error_process = ErrorProcess(self.in_queue, self.out_queue, self.error_queue, self.consumers, self.close_event)
        self.error_process.start()

        try:
            self.in_queue.join()
        except KeyboardInterrupt:
            return

        print('All tests finished, gathering results')
        while True:
            try:
                (_, settings), stats = self.out_queue.get(block=False)
            except queue.Empty:
                break
            else:
                if settings.name not in self.results:
                    self.results[settings.name] = (settings, TestStats())

                self.results[settings.name][1].append(stats)

        self.close()

    def save_results(self):
        dt = datetime.now().isoformat().replace(':', '-')
        if not os.path.isdir('results'):
            os.mkdir('results')

        fn = f'results/{dt}.json'

        data = [{**settings.to_dict(), 'stats': stats.to_dict(self.include_raw)} for settings, stats in self.results.values()]
        with open(fn, 'w') as f:
            json.dump(data, f, indent=4)

        print(f'Saved results to {fn}')

    def close(self):
        self.save_results()
        self.close_event.set()
        self.error_process.join()

        self.in_queue.close()
        self.out_queue.close()
        self.error_queue.close()
        self.error_process.close()
