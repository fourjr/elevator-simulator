import glob
import importlib
import os
from typing import Callable, Dict


def get_tests() -> Dict[str, Callable]:
    tests = {}
    for i in glob.iglob('tests/*.py'):
        if not i.endswith('__main__.py'):
            module = importlib.import_module(i.replace(os.path.sep, '.')[:-3])
            if not hasattr(module, 'run_test'):
                raise AttributeError(f'{module} does not have a run_test function')

            tests[module.__name__] = module.run_test

    return tests


if __name__ == '__main__':
    tests = get_tests()
    print(f'[SUITE] [I] Found {len(tests)} tests')
    for name, func in tests.items():
        print(f'[SUITE] [I] Running {name}')
        func()
