import copy
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

from enums import Constants, LogLevel, LogOrigin
from errors import TestTimeout
from models import (
    CombinedStats,
    ElevatorAlgorithm,
    Load,
    SimulationStats,
    ElevatorManager,
)
from utils import jq_join_timeout, load_algorithms, save_algorithm


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


@dataclass
class TestSettings:
    """Settings for a single test

    name: str
        Name of the test
    seed: int
        Seed for the random number generator
    speed: int
        Speed of the simulation in relative ticks # TODO: improve explanation
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
    """

    name: str
    seed: int
    speed: int
    floors: int
    num_elevators: int
    num_passengers: int
    algorithm_name: str
    total_iterations: int
    max_load: int
    loads: List[Load] = field(default_factory=list)

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
            'seed': self.seed,
            'speed': self.speed,
            'floors': self.floors,
            'num_elevators': self.num_elevators,
            'num_passengers': self.num_passengers,
            'total_iterations': iteration_count or self.total_iterations,
        }


class TestSuiteConsumer(ElevatorManager, mp.Process):
    def __init__(self, in_queue, out_queue, error_queue, export_queue):
        self.algorithms = load_algorithms()
        super().__init__(
            self,
            None,
            self.algorithms[Constants.DEFAULT_ALGORITHM],
            gui=False,
            log_func=self.log_message,
        )
        self._running = False
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.error_queue = error_queue
        self.export_queue = export_queue

        self._process = mp.Process(target=self.process_loop, daemon=True)

        self.name = self._process.name
        self.latest_load_move = 0
        self.previous_loads = []
        self.current_simulation = None

    @property
    def running(self):
        return self._running

    def start(self):
        self._process.start()

    def close(self):
        self._process.terminate()
        self._process.join()
        self._process.close()
        super().close()

    def process_loop(self):
        try:
            while True:
                n_iter, settings = self.in_queue.get()

                self.current_simulation = (n_iter, settings)

                algo = self.algorithms[settings.algorithm_name]
                algo.name = settings.algorithm_name
                self.reset(algo)
                self.algorithm.rnd = random.Random((settings.seed + n_iter) % 2 ** 32)

                self.set_speed(settings.speed)
                self.set_floors(settings.floors)
                self.set_max_load(settings.max_load)

                settings.init_passengers(self.algorithm.rnd)

                elevator_floors = []
                for _ in range(settings.num_elevators):
                    elevator_floors.append(self.algorithm.rnd.randint(1, settings.floors))

                for floor in elevator_floors:
                    self.add_elevator(floor)

                for load in settings.loads:
                    self.algorithm.add_load(load)

                # save
                if self.export_queue is not None:
                    name = f'{settings.name}_{n_iter}'
                    self.export_queue.put((name, copy.deepcopy(self.algorithm)))

                self.active = True
                self.log_message(
                    LogLevel.INFO,
                    f'{self.name} START SIMULATION: {n_iter=} {settings.name=}',
                    LogOrigin.TEST,
                )

                try:
                    self.start_simulation()
                except TestTimeout as e:
                    # continue with next simulation
                    self.log_message(
                        LogLevel.WARNING,
                        f'{self.name} SKIP SIMULATION (TIMEOUT): {n_iter=} {settings.name=} {self.current_tick=}',
                        LogOrigin.TEST,
                    )
                else:
                    self.log_message(
                        LogLevel.INFO,
                        f'{self.name} END SIMULATION: {n_iter=} {settings.name=} {self.current_tick=}',
                        LogOrigin.TEST,
                    )
                    self.out_queue.put(((n_iter, settings), self.algorithm.stats))

                self.in_queue.task_done()

        except KeyboardInterrupt:
            return
        except Exception as e:
            # mark as done although errored
            self.in_queue.task_done()

            # need to format first as pickle will remove the traceback
            e.formatted_exception = traceback.format_exc().strip()

            if self.current_simulation is not None:
                n_iter, settings = self.current_simulation
                self.log_message(
                    LogLevel.ERROR,
                    f'{self.name} ERROR SIMULATION: {n_iter=} {settings.name=} {self.current_tick=}',
                    LogOrigin.TEST,
                )
            else:
                self.log_message(
                    LogLevel.ERROR,
                    f'{self.name} ERROR SIMULATION: {self.current_tick=}',
                    LogOrigin.TEST,
                )

            self.error_queue.put((self.name, e))

    def on_tick(self):
        if self.running is True and self.algorithm.simulation_running is False:
            self.end_simulation()

        # frozen loads
        if self.current_tick - self.latest_load_move > 500:
            self.end_simulation()
            n_iter, settings = self.current_simulation
            self.log_message(
                LogLevel.ERROR,
                f'{self.name=} TIMEOUT: {n_iter=} {settings.name=}',
                LogOrigin.TEST,
            )
            raise TestTimeout(self.name, n_iter, settings)

    def on_load_move(self, _):
        self.latest_load_move = self.current_tick

    def start_simulation(self):
        self._running = True
        self.loop()

    def end_simulation(self):
        self._running = False

    def log_message(self, level: LogLevel, message, origin=LogOrigin.SIMULATION):
        if level not in (LogLevel.DEBUG, LogLevel.TRACE, LogLevel.INFO) or origin == LogOrigin.TEST:
            print(level.name, message)

    def __getstate__(self):
        obj = self.__dict__.copy()
        del obj['_process']
        return obj


class BackgroundProcess(mp.Process):
    def __init__(
        self,
        in_queue,
        out_queue,
        error_queue,
        export_queue,
        consumers: List[TestSuiteConsumer],
        close_event,
    ):
        super().__init__()
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.error_queue = error_queue
        self.export_queue = export_queue
        self.consumers = consumers
        self.close_event = close_event

    def is_closed(self):
        return self.close_event.is_set()

    def run(self):
        try:
            while not self.is_closed():
                while not self.is_closed():
                    try:
                        name, e = self.error_queue.get(timeout=0.1)
                    except queue.Empty:
                        break
                    else:
                        del self.consumers[name]
                        consumer = TestSuiteConsumer(
                            self.in_queue,
                            self.out_queue,
                            self.error_queue,
                            self.export_queue,
                        )
                        consumer.start()
                        self.consumers[consumer.name] = consumer

                        print(f'[E_HANDLER] INFO {name} died, restarting as {consumer.name}')
                        print(e.formatted_exception)
                        self.error_queue.task_done()

                if self.export_queue is not None:
                    while not self.is_closed():
                        try:
                            name, algo = self.export_queue.get(timeout=0.2)
                        except queue.Empty:
                            break
                        else:
                            dt = datetime.now().isoformat().replace(':', '-')
                            fn = f'{dt}_{name}.esi'
                            save_algorithm(algo, fn)
                            print(f'[F_HANDLER] INFO {name} exported and saved')
                            self.export_queue.task_done()
        except KeyboardInterrupt:
            return


class TestSuite:
    def __init__(self, tests, **options):
        """Creates a test suite

        tests: List[TestSettings]
            Various tests to be run
        **export_artefacts: bool
            Default: True
            Whether to export the artefacts of the simulation
        **max_processes: int
            Default: None
            Maximum number of processes to use
        **include_raw_stats: bool
            Default: True
            Whether to include the raw stats in the output
        """
        self.tests: List[TestSettings] = tests
        self.in_queue: JoinableQueue[Tuple[int, TestSettings]] = JoinableQueue()
        self.out_queue: Queue[Tuple[Tuple[int, TestSettings], SimulationStats]] = Queue()
        self.error_queue: JoinableQueue[Tuple[str, Exception]] = JoinableQueue()
        self.export_queue: JoinableQueue[Tuple[str, ElevatorAlgorithm]] = JoinableQueue()

        self.close_event = mp.Event()
        self.export_artefacts = options.pop('export_artefacts', True)
        self.include_raw_stats = options.pop('include_raw_stats', True)

        self.results: dict[str, Tuple[TestSettings, TestStats]] = {}

        hard_max_processes = min(mp.cpu_count() - 1, sum(x.total_iterations for x in self.tests))

        max_processes = options.pop('max_processes', None)
        if max_processes is None:
            self.max_processes = hard_max_processes
        else:
            self.max_processes = min(max_processes, hard_max_processes)

        self.init_tests()

        self.consumers = {}
        self.background_process = BackgroundProcess(
            self.in_queue,
            self.out_queue,
            self.error_queue,
            self.export_queue if self.export_artefacts else None,
            self.consumers,
            self.close_event,
        )

    def init_tests(self):
        """Initialises the tests and prepare for execution"""
        for test in self.tests:
            for i in range(test.total_iterations):
                self.in_queue.put((i + 1, test))

    def start(self):
        """Starts the Test Suite"""
        for _ in range(self.max_processes):
            consumer = TestSuiteConsumer(
                self.in_queue,
                self.out_queue,
                self.error_queue,
                self.export_queue if self.export_artefacts else None,
            )
            self.consumers[consumer.name] = consumer

        try:
            self.background_process.start()
            for p in self.consumers.values():
                p.start()

            while True:
                try:
                    jq_join_timeout(self.in_queue, timeout=0.1)
                except TimeoutError:
                    pass
                else:
                    break
        except Exception:
            self.close(force=True)
            raise
        except KeyboardInterrupt:
            self.close(force=True)
            raise
        else:
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
            self.save_results()
            self.close()

    def save_results(self):
        dt = datetime.now().isoformat().replace(':', '-')
        if not os.path.isdir('results'):
            os.mkdir('results')

        fn = f'results/{dt}.json'

        data = [
            {
                **settings.to_dict(len(stats)),
                'stats': stats.to_dict(self.include_raw_stats),
            }
            for settings, stats in self.results.values()
        ]
        with open(fn, 'w') as f:
            json.dump(data, f, indent=4)

        print(f'Saved results to {fn}')

    def close(self, *, force=False):
        self.close_event.set()
        if force:
            self.background_process.terminate()
            self.background_process.join()

            # allow process to be abruptly stopped without waiting for queues to empty
            # https://docs.python.org/3/library/multiprocessing.html#pipes-and-queues
            self.in_queue.cancel_join_thread()
            self.out_queue.cancel_join_thread()
            self.error_queue.cancel_join_thread()
            self.export_queue.cancel_join_thread()
        else:
            self.background_process.join()
            self.export_queue.join()

        self.in_queue.close()
        self.out_queue.close()
        self.export_queue.close()
        self.error_queue.close()
        self.background_process.close()
