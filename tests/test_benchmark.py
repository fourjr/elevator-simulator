"""Run a typical benchmark with 100 iterations"""
import sys
import time

from models.algorithm import load_algorithms
from suite import TestSettings, TestSuite


def run_test():
    test_only = ' '.join(sys.argv[1:]) or None
    SEED = 1234
    START_TIME = time.perf_counter()
    options = {
        'include_raw_stats': False,
        'export_artefacts': True,
    }

    tests = []
    algorithms = load_algorithms()
    for algorithm_name in algorithms.keys():
        if test_only is not None and algorithm_name != test_only:
            continue
        tests.extend(
            (
                TestSettings(
                    name='Busy',
                    algorithm_name=algorithm_name,
                    seed=SEED,
                    floors=80,
                    num_elevators=16,
                    num_passengers=1600,
                    total_iterations=100,
                    max_load=15 * 60,
                ),
                TestSettings(
                    name='Slow',
                    algorithm_name=algorithm_name,
                    seed=SEED,
                    floors=10,
                    num_elevators=2,
                    num_passengers=100,
                    total_iterations=100,
                    max_load=15 * 60,
                ),
            )
        )

    suite = TestSuite(tests, **options)
    suite.start()
    print(suite.format_results())

    time_taken = time.perf_counter() - START_TIME
    print(f'Total time: {time_taken:.2f}s')
