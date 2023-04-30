import json
import multiprocessing as mp
import os
import queue
from datetime import datetime
from multiprocessing import JoinableQueue, Queue, Pool
from typing import List, Tuple

import colorama

from constants import LogLevel, LogOrigin
from models import ElevatorAlgorithm, SimulationStats
from suite import BackgroundProcess, TestStats, TestSuiteConsumer
from suite.manager import run_loop


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
        self.tests: List['TestSettings'] = tests
        self.mp_manager = mp.Manager()
        self.export_queue: JoinableQueue[Tuple[str, ElevatorAlgorithm]] = self.mp_manager.JoinableQueue()
        self.log_queue: JoinableQueue[Tuple[LogOrigin, LogLevel, str]] = self.mp_manager.JoinableQueue()

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

        self.results: dict[str, Tuple['TestSettings', TestStats]] = {}
        self.did_not_complete: List['TestSettings'] = []

        hard_max_processes = min(mp.cpu_count() - 1, sum(x.total_iterations for x in self.tests))

        max_processes = options.pop('max_processes', None)
        if max_processes is None:
            self.max_processes = hard_max_processes
        else:
            self.max_processes = min(max_processes, hard_max_processes)

        self.consumers = []
        self.background_process = BackgroundProcess(
            self.export_queue if self.export_artefacts else None,
            self.log_queue,
            self.close_event,
            self.log_levels,
        )

    def start(self):
        """Starts the Test Suite"""
        try:
            # for _ in range(self.max_processes):
            # TODO: make a functioanlity where there is a list of consumers to fetch from
            # and only be allowed to fetch free ones
            for test in self.tests:
                for i in range(test.total_iterations):
                    self.consumers.append(TestSuiteConsumer(self.export_queue, self.log_queue, self.log_levels))

            self.log_queue.put((LogOrigin.TEST, LogLevel.INFO, 'Starting test suite'))

            self.background_process.start()

            args = []
            for test in self.tests:
                for i in range(test.total_iterations):
                    args.append(((i + 1, test), self.consumers[i]))

            with Pool(processes=self.max_processes) as pool:
                out = pool.map_async(run_loop, args)

                while not out.ready():
                    out.wait(timeout=0.1)

            self.log_queue.put((LogOrigin.TEST, LogLevel.INFO, 'All tests finished, gathering results'))

            res = out.get(timeout=0.1)
            for (n_iter, settings), stats in res:
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
        successful_iterations = sum(len(x[1]) for x in self.results.values())

        final_fmt.append(f'Total iterations: {total_iterations}')
        final_fmt.append(f'Failed iterations: {failed_iterations}')
        if failed_iterations > 0:
            final_fmt.append('Failed tests:')
            for n_iter, test in self.did_not_complete:
                final_fmt.append(f'  - {test.name}_{test.algorithm_name}_{n_iter}')

        final_fmt.append(f'Successful iterations: {successful_iterations}')

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
            if self.background_process.is_alive():
                self.background_process.terminate()
                self.background_process.join()

            # allow process to be abruptly stopped without waiting for queues to empty
            # https://docs.python.org/3/library/multiprocessing.html#pipes-and-queues
            # self.in_queue.cancel_join_thread()
            # self.out_queue.cancel_join_thread()
            # self.error_queue.cancel_join_thread()
            # self.export_queue.cancel_join_thread()
            # self.log_queue.cancel_join_thread()
        else:
            self.export_queue.join()
            self.log_queue.join()
            self.close_event.set()
            self.background_process.join()

        # self.in_queue.close()
        # self.out_queue.close()
        # self.error_queue.close()
        # self.export_queue.close()
        # self.log_queue.close()
        self.mp_manager.shutdown()
        self.background_process.close()
