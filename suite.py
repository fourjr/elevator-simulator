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

import colorama

from constants import Constants, Infinity, LogLevel, LogOrigin
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


class TestSuiteConsumer(ElevatorManager, mp.Process):
    def __init__(self, in_queue, out_queue, error_queue, export_queue, log_queue, log_levels):
        self.algorithms = load_algorithms()
        super().__init__(
            self,
            None,
            self.algorithms[Constants.DEFAULT_ALGORITHM],
            gui=False,
            log_func=self.log_message_simulation,
        )
        self._running = False
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.error_queue = error_queue
        self.export_queue = export_queue
        self.log_queue = log_queue
        self.log_levels = log_levels

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

                if settings.init_function is not None:
                    settings.init_function(self.algorithm)

                # save
                if self.export_queue is not None:
                    name = f'{settings.name}_{settings.algorithm_name}_{n_iter}'
                    self.export_queue.put((name, copy.deepcopy(self.algorithm)))

                self.active = True
                self.log_message(
                    LogOrigin.TEST,
                    LogLevel.TRACE,
                    f'{self.name} START SIMULATION: {n_iter=} {settings.name=} {settings.algorithm_name=}',
                )

                try:
                    self.start_simulation()
                except TestTimeout as e:
                    # continue with next simulation
                    self.out_queue.put(((n_iter, settings), e))
                    self.log_message(
                        LogOrigin.TEST,
                        LogLevel.WARNING,
                        f'{self.name} SKIP SIMULATION (TIMEOUT): {n_iter=} {settings.name=} {settings.algorithm_name=}',
                    )
                else:
                    self.log_message(
                        LogOrigin.TEST,
                        LogLevel.TRACE,
                        f'{self.name} END SIMULATION: {n_iter=} {settings.name=}  {settings.algorithm_name=}',
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
                    LogOrigin.TEST,
                    LogLevel.ERROR,
                    f'{self.name} ERROR SIMULATION: {n_iter=} {settings.name=} {settings.algorithm_name=}\n\n{e.formatted_exception}',
                )
            else:
                self.log_message(
                    LogOrigin.TEST,
                    LogLevel.ERROR,
                    f'{self.name} ERROR SIMULATION\n\n{e.formatted_exception}',
                )

            self.out_queue.put(((n_iter, settings), e))
            self.error_queue.put((self.name, e))

    def on_tick(self):
        if self.running is True and self.algorithm.simulation_running is False:
            self.end_simulation()

        # frozen loads
        if self.algorithm.tick_count - self.latest_load_move > 500:
            self.end_simulation()
            n_iter, settings = self.current_simulation
            self.log_message(
                LogOrigin.TEST,
                LogLevel.ERROR,
                f'{self.name=} TIMEOUT: {n_iter=} {settings.name=} {settings.algorithm_name=}',
            )
            raise TestTimeout(self.name, n_iter, settings)

    def on_load_move(self, _):
        self.latest_load_move = self.algorithm.tick_count

    def start_simulation(self):
        self._running = True
        self.loop()

    def end_simulation(self):
        self._running = False

    def log_message_simulation(self, level, message):
        self.log_message(LogOrigin.SIMULATION, level, message)

    def log_message(self, origin, level, message):
        if level >= self.log_levels[origin]:
            self.log_queue.put((origin, level, message))

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
        log_queue,
        consumers: List[TestSuiteConsumer],
        close_event,
        log_levels,
    ):
        super().__init__()
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.error_queue = error_queue
        self.export_queue = export_queue
        self.log_queue = log_queue
        self.consumers = consumers
        self.close_event = close_event
        self.log_levels = log_levels

    def is_closed(self):
        return self.close_event.is_set()

    def run(self):
        try:
            while not self.is_closed():
                while not self.is_closed():
                    try:
                        name, e = self.error_queue.get(timeout=0.01)
                    except queue.Empty:
                        break
                    else:
                        del self.consumers[name]
                        consumer = TestSuiteConsumer(
                            self.in_queue,
                            self.out_queue,
                            self.error_queue,
                            self.export_queue,
                            self.log_queue,
                            self.log_levels,
                        )
                        consumer.start()
                        self.consumers[consumer.name] = consumer

                        self.log_queue.put(
                            (LogOrigin.ERROR_HANDLER, LogLevel.INFO, f'{name} died, restarting as {consumer.name}')
                        )
                        self.error_queue.task_done()

                if self.export_queue is not None:
                    while not self.is_closed():
                        try:
                            name, algo = self.export_queue.get(timeout=0.01)
                        except queue.Empty:
                            break
                        else:
                            dt = datetime.now().isoformat().replace(':', '-')
                            fn = f'{dt}_{name}.esi'
                            save_algorithm(algo, fn)
                            self.log_queue.put(
                                (LogOrigin.FILE_HANDLER, LogLevel.TRACE, f'{name} exported to {fn}')
                            )
                            self.export_queue.task_done()

                while not self.is_closed():
                    try:
                        origin, level, message = self.log_queue.get(timeout=0.01)
                    except queue.Empty:
                        break
                    else:
                        if level >= self.log_levels[origin]:
                            print(f'[{origin.name}] [{level.name[0]}] {message}')

                        self.log_queue.task_done()

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
        **log_levels: Dict[LogOrigin, List[LogLevel]]
        """
        self.tests: List[TestSettings] = tests
        self.in_queue: JoinableQueue[Tuple[int, TestSettings]] = JoinableQueue()
        self.out_queue: Queue[Tuple[Tuple[int, TestSettings], SimulationStats | Exception]] = Queue()
        self.error_queue: JoinableQueue[Tuple[str, Exception]] = JoinableQueue()
        self.export_queue: JoinableQueue[Tuple[str, ElevatorAlgorithm]] = JoinableQueue()
        self.log_queue: JoinableQueue[Tuple[LogOrigin, LogLevel, str]] = JoinableQueue()

        self.close_event = mp.Event()
        self.export_artefacts = options.pop('export_artefacts', True)
        self.include_raw_stats = options.pop('include_raw_stats', True)
        self.log_levels = options.pop(
            'log_levels',
            {
                LogOrigin.SIMULATION: LogLevel.WARNING,
                LogOrigin.TEST: LogLevel.INFO,
                LogOrigin.ERROR_HANDLER: LogLevel.INFO,
                LogOrigin.FILE_HANDLER: LogLevel.INFO,
            },
        )

        self.results: dict[str, Tuple[TestSettings, TestStats]] = {}
        self.did_not_complete: List[TestSettings] = []

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
            self.log_queue,
            self.consumers,
            self.close_event,
            self.log_levels,
        )

    def init_tests(self):
        """Initialises the tests and prepare for execution"""
        for test in self.tests:
            for i in range(test.total_iterations):
                self.in_queue.put((i + 1, test))

    def start(self):
        """Starts the Test Suite"""
        try:
            for _ in range(self.max_processes):
                consumer = TestSuiteConsumer(
                    self.in_queue,
                    self.out_queue,
                    self.error_queue,
                    self.export_queue if self.export_artefacts else None,
                    self.log_queue,
                    self.log_levels,
                )
                self.consumers[consumer.name] = consumer

            self.log_queue.put((LogOrigin.TEST, LogLevel.INFO, 'Starting test suite'))

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

            self.log_queue.put((LogOrigin.TEST, LogLevel.INFO, 'All tests finished, gathering results'))
            while True:
                try:
                    (n_iter, settings), stats = self.out_queue.get(block=False)
                except queue.Empty:
                    break
                else:
                    if isinstance(stats, Exception):
                        self.did_not_complete.append((n_iter, settings))
                    else:
                        if settings.id not in self.results:
                            self.results[settings.id] = (settings, TestStats())
                        self.results[settings.id][1].append(stats)

            self.did_not_complete.sort(key=lambda x: ((x[1].name, x[1].algorithm_name, x[0])))
            self.save_results()
        except Exception:
            self.close(force=True)
            raise
        except KeyboardInterrupt:
            self.close(force=True)
            raise
        else:
            self.close()

    def format_results(self):
        """Formats the results for printing"""
        colorama.init()
        test_rows = {}
        final_fmt = []

        final_fmt.append('=============')
        final_fmt.append('Test Complete')
        final_fmt.append('=============')
        total_iterations = sum(x.total_iterations for x in self.tests)
        failed_iterations = len(self.did_not_complete)
        final_fmt.append(f'Total iterations: {total_iterations}')
        final_fmt.append(f'Failed iterations: {failed_iterations}')
        if failed_iterations > 0:
            final_fmt.append('Failed tests:')
            for n_iter, test in self.did_not_complete:
                final_fmt.append(f'  - {test.name}_{test.algorithm_name}_{n_iter}')

        final_fmt.append(f'Successful iterations: {total_iterations - failed_iterations}')

        if self.results:
            for settings, results in sorted(self.results.values(), key=lambda x: x[1].ticks.mean):
                fmt = (
                    settings.algorithm_name,
                    str(len(results)),
                    f'{results.ticks.mean:.2f} ({results.ticks.median:.2f})',
                    f'{results.wait_time.mean:.2f} ({results.wait_time.median:.2f})',
                    f'{results.time_in_lift.mean:.2f} ({results.time_in_lift.median:.2f})',
                    f'{results.occupancy.mean:.2f} ({results.occupancy.median:.2f})',
                )
                if settings.name not in test_rows:
                    test_rows[settings.name] = [(settings.name.upper(), 'NUM', 'TICK', 'WAIT', 'TIL', 'OCC')]

                test_rows[settings.name].append(fmt)

            all_rows = [x for y in test_rows.values() for x in y]
            maxlens = [max(len(str(x)) + 2 for x in col) for col in zip(*all_rows)]

            final_fmt.append('')
            for test_fmt in test_rows.values():
                test_fmt.insert(1, tuple('-' * (maxlens[i] - 2) for i in range(len(maxlens))))
                for row in test_fmt:
                    final_fmt.append(''.join(f'{x:<{maxlens[i]}}' for i, x in enumerate(row)))
                final_fmt.append('')

        return '\n'.join(final_fmt)

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

        self.log_queue.put((LogOrigin.TEST, LogLevel.INFO, f'Saved results to {fn}'))

    def close(self, *, force=False):
        if force:
            self.close_event.set()
            self.background_process.terminate()
            self.background_process.join()

            # allow process to be abruptly stopped without waiting for queues to empty
            # https://docs.python.org/3/library/multiprocessing.html#pipes-and-queues
            self.in_queue.cancel_join_thread()
            self.out_queue.cancel_join_thread()
            self.error_queue.cancel_join_thread()
            self.export_queue.cancel_join_thread()
            self.log_queue.cancel_join_thread()
        else:
            self.export_queue.join()
            self.log_queue.join()
            self.close_event.set()
            self.background_process.join()

        self.in_queue.close()
        self.out_queue.close()
        self.error_queue.close()
        self.export_queue.close()
        self.log_queue.close()
        self.background_process.close()
