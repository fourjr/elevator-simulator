"""Run a test suite from a JSON file.

Usage: Execute script with the path to the JSON file as the first argument.
Example: python test_json.py test.example.json
"""
import sys
import time

from suite import TestSettings, TestSuite
from utils import load_algorithms


if __name__ == "__main__":

    test_only = ' '.join(sys.argv[1:]) or None
    SEED = 1234
    START_TIME = time.perf_counter()
    options = {
        'max_processes': None,
        'include_raw_stats': False,
        'export_artefacts': True
    }

    tests = []
    algorithms = load_algorithms()
    for algorithm_name in algorithms.keys():
        if test_only is not None and algorithm_name != test_only:
            continue
        tests.extend((
            TestSettings(
                name=f'Busy {algorithm_name}',
                algorithm_name=algorithm_name,
                seed=SEED,
                speed=1000,
                floors=80,
                num_elevators=16,
                num_passengers=1600,
                total_iterations=10,
                max_load=15 * 60
            ),
            TestSettings(
                name=f'Slow {algorithm_name}',
                algorithm_name=algorithm_name,
                seed=SEED,
                speed=1000,
                floors=10,
                num_elevators=2,
                num_passengers=100,
                total_iterations=10,
                max_load=15 * 60
            )
        ))

    suite = TestSuite(tests, **options)
    suite.start()

    busy_rows = [
        ("BUSY", "TICK", "WAIT", "TIL", "OCC")
    ]
    slow_rows = [
        ("SLOW", "TICK", "WAIT", "TIL", "OCC")
    ]

    for settings, results in sorted(suite.results.values(), key=lambda x: x[0].name):
        fmt = (
            settings.algorithm_name, f"{results.ticks.mean:.2f} ({results.ticks.median:.2f})", 
            f"{results.wait_time.mean:.2f} ({results.wait_time.median:.2f})",
            f"{results.time_in_lift.mean:.2f} ({results.time_in_lift.median:.2f})",
            f"{results.occupancy.mean:.2f} ({results.occupancy.median:.2f})"
        )
        if settings.name.startswith("Busy"):
            busy_rows.append(fmt)
        elif settings.name.startswith("Slow"):
            slow_rows.append(fmt)

    # table
    maxlens = [max(len(str(x)) + 2 for x in col) for col in zip(*(busy_rows + slow_rows))]
    busy_rows.insert(1, tuple("-" * (maxlens[i] - 2) for i in range(len(maxlens))))
    slow_rows.insert(1, tuple("-" * (maxlens[i] - 2) for i in range(len(maxlens))))

    for row in busy_rows:
        print("  ".join(f"{x:<{maxlens[i]}}" for i, x in enumerate(row)))
    print()
    for row in slow_rows:
        print("  ".join(f"{x:<{maxlens[i]}}" for i, x in enumerate(row)))
    print()

    time_taken = time.perf_counter() - START_TIME
    print(f"Total time: {time_taken:.2f}s")
