"""Run a test suite simulating a busy office day"""
import sys
import time
from models import Load
from models import ElevatorAlgorithm

from suite import TestSettings, TestSuite
from utils import load_algorithms


def morning_init(algo: ElevatorAlgorithm):
    for _ in range(500):
        dest = algo.rnd.randint(2, algo.floors)
        algo.loads.append(Load(1, dest, 60))

    for _ in range(100):
        init = algo.rnd.randint(2, algo.floors)
        algo.loads.append(Load(init, 1, 60))


def evening_init(algo: ElevatorAlgorithm):
    for _ in range(600):
        init = algo.rnd.randint(2, algo.floors)
        algo.loads.append(Load(init, 1, 60))


if __name__ == '__main__':
    test_only = ' '.join(sys.argv[1:]) or None
    SEED = 1234
    START_TIME = time.perf_counter()
    options = {
        'max_processes': None,
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
                    name='Morning',
                    algorithm_name=algorithm_name,
                    seed=SEED,
                    floors=50,
                    num_passengers=100,
                    num_elevators=8,
                    total_iterations=10,
                    max_load=15 * 60,
                    init_function=morning_init,
                ),
                TestSettings(
                    name='Evening',
                    algorithm_name=algorithm_name,
                    seed=SEED,
                    floors=50,
                    num_passengers=100,
                    num_elevators=8,
                    total_iterations=10,
                    max_load=15 * 60,
                    init_function=evening_init,
                ),
            )
        )

    suite = TestSuite(tests, **options)
    suite.start()
    print(suite.format_results())

    time_taken = time.perf_counter() - START_TIME
    print(f'Total time: {time_taken:.2f}s')
