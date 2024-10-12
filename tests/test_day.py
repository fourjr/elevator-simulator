"""Run a test suite simulating a full day"""
import sys
import time
from models import Load
from models import ElevatorAlgorithm

from models.algorithm import load_algorithms
from suite import TestSettings, TestSuite


def add_loads(algo, count, popular_floors):
    all_floors = list(range(1, algo.floors + 1))
    for _ in range(count // 2):
        picked_popular = algo.rnd.choice(popular_floors)
        while True:
            dest = algo.rnd.choice(all_floors)
            if dest > picked_popular:
                break
        algo.loads.append(Load(picked_popular, dest, 60))

    for _ in range(count // 2):
        picked_popular = algo.rnd.choice(popular_floors)
        while True:
            init = algo.rnd.choice(all_floors)
            if init < picked_popular:
                break
        algo.loads.append(Load(init, picked_popular, 60))


def init_func(algo: ElevatorAlgorithm):
    algo.popular_floors = algo.rnd.sample(range(2, algo.floors), 5)

    add_loads(algo, 1000, algo.popular_floors)


def on_tick(algo: ElevatorAlgorithm):
    if len(algo.loads) < 30:
        if not hasattr(algo, 'add_load_counter'):
            algo.add_load_counter = 0
        if algo.add_load_counter >= 10:
            return

        add_loads(algo, 100, algo.popular_floors)
        algo.add_load_counter += 1


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

        tests.append(
            TestSettings(
                name='Day',
                algorithm_name=algorithm_name,
                seed=SEED,
                floors=50,
                num_passengers=100,
                num_elevators=8,
                total_iterations=50,
                max_load=15 * 60,
                init_function=init_func,
                on_tick=on_tick,
            )
        )

    suite = TestSuite(tests, **options)
    suite.start()
    print(suite.format_results())

    time_taken = time.perf_counter() - START_TIME
    print(f'Total time: {time_taken:.2f}s')
