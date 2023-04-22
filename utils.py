import glob
import importlib
import os
import statistics
from typing import List

from errors import InvalidAlgorithm
from models import ElevatorAlgorithm


class Unicode:
    UP = "\u2191"
    DOWN = "\u2193"
    ARROW = "\u2192"


class Constants:
    DEFAULT_ALGORITHM = "Knuth"
    MAX_PROCESSES = 3

def load_algorithms() -> dict[str, ElevatorAlgorithm]:
    algorithms = {}
    for i in glob.iglob('algorithms/*.py'):
        module = importlib.import_module(i.replace(os.path.sep, '.')[:-3])
        if not hasattr(module, '__algorithm__'):
            raise InvalidAlgorithm(f'Algorithm in {module} is not defined')
        if not hasattr(module, '__name__'):
            raise InvalidAlgorithm(f'Name in {module} is not defined')

        algorithm = module.__algorithm__
        if not issubclass(algorithm, ElevatorAlgorithm):
            raise InvalidAlgorithm(f'Algorithm in {module} is not a subclass of ElevatorAlgorithm')

        algorithm.name = module.__name__
        algorithms[algorithm.name] = algorithm

    return algorithms
