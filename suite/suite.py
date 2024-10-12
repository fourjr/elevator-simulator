import json
import logging
import multiprocessing as mp
import os
import queue
import tqdm
from datetime import datetime
from multiprocessing import JoinableQueue, Pool
from typing import List, Tuple

import colorama

from utils import LogOrigin, get_log_name
from models import ElevatorAlgorithm
from suite import BackgroundProcess, TestStats, TestSuiteManager, ManagerPool, run_loop


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
        **log_levels: Dict[LogOrigin, List[int]]
        """
        self.tests: List['TestSettings'] = tests
        self.mp_manager = mp.Manager()
        self.export_queue: JoinableQueue[Tuple[str, ElevatorAlgorithm]] = self.mp_manager.JoinableQueue()
        self.log_queue: JoinableQueue[Tuple[LogOrigin, int, str]] = self.mp_manager.JoinableQueue()

        self.close_event = mp.Event()
        self.export_artefacts = options.pop('export_artefacts', True)
        self.include_raw_stats = options.pop('include_raw_stats', True)
        self.log_levels = {
            LogOrigin.SIMULATION: logging.WARNING,
            LogOrigin.TEST: logging.INFO,
            LogOrigin.ERROR_HANDLER: logging.INFO,
            LogOrigin.FILE_HANDLER: logging.INFO,
        }

        if options.get('log_levels'):
            self.log_levels.update(options.pop('log_levels'))

        self.results: dict[str, Tuple['TestSettings', TestStats]] = {}
        self.did_not_complete: List['TestSettings'] = []

        hard_max_processes = min(mp.cpu_count() - 1, sum(x.total_iterations for x in self.tests))

        max_processes = options.pop('max_processes', hard_max_processes)
        self.max_processes = min(max_processes, hard_max_processes)

        self.algo_manager_pool = ManagerPool(self.mp_manager)
        self.background_process = BackgroundProcess(
            self.export_queue if self.export_artefacts else None,
            self.log_queue,
            self.close_event,
            self.log_levels,
        )

        if options:
            raise ValueError(f'Unknown options: {options}')

    def check_log(self, bar=None):
        while not self.close_event.is_set():
            try:
                origin, level, message = self.log_queue.get(timeout=0.01)
            except queue.Empty:
                break
            else:
                if level >= self.log_levels[origin]:
                    name = get_log_name(level)
                    fmt = f'[{origin.name}] [{name[0]}] {message}'
                    if bar is None:
                        print(fmt)
                    else:
                        bar.write(fmt)

                self.log_queue.task_done()

    def start(self):
        """Starts the Test Suite"""
        try:
            for _ in range(self.max_processes):
                self.algo_manager_pool.append(TestSuiteManager(self.export_queue, self.log_queue, self.log_levels))

            self.log_queue.put((LogOrigin.TEST, logging.INFO, 'Starting test suite'))
            self.background_process.start()

            args = []
            for test in self.tests:
                for i in range(test.total_iterations):
                    args.append(((i + 1, test), self.algo_manager_pool))

            res = []
            with Pool(processes=self.max_processes) as pool:
                with tqdm.tqdm(total=len(args), dynamic_ncols=True, unit='sim') as bar:
                    it = pool.imap_unordered(run_loop, args)

                    while True:
                        try:
                            res.append(it.next(timeout=0.1))
                        except StopIteration:
                            break
                        except mp.TimeoutError:
                            bar.update(0)
                            continue
                        else:
                            bar.update()
                        finally:
                            self.check_log(bar)

            self.log_queue.put((LogOrigin.TEST, logging.INFO, 'All tests finished, gathering results'))

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

        self.log_queue.put((LogOrigin.TEST, logging.INFO, f'Saved results to {fn}'))

    def close(self, *, force=False):
        if force:
            self.close_event.set()
            if self.background_process.is_alive():
                self.background_process.terminate()
                self.background_process.join()
        else:
            self.export_queue.join()
            self.check_log()
            self.log_queue.join()
            self.close_event.set()
            self.background_process.join()

        self.algo_manager_pool.close()
        self.background_process.close()
        self.mp_manager.shutdown()
