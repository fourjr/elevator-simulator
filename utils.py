import glob
import importlib
import os
import statistics
from typing import List

from errors import InvalidManager
from models import ElevatorManager


class Unicode:
    UP = "\u2191"
    DOWN = "\u2193"
    ARROW = "\u2192"


class Constants:
    DEFAULT_ALGORITHM = "Knuth"

def load_algorithms():
    algorithms = {}
    for i in glob.iglob('managers/*.py'):
        module = importlib.import_module(i.replace(os.path.sep, '.')[:-3])
        if not hasattr(module, '__manager__'):
            raise InvalidManager(f'Manager in {module} is not defined')
        if not hasattr(module, '__name__'):
            raise InvalidManager(f'Name in {module} is not defined')

        manager = module.__manager__
        if not issubclass(manager, ElevatorManager):
            raise InvalidManager(f'Manager in {module} is not a subclass of ElevatorManager')

        manager.name = module.__name__
        algorithms[manager.name] = manager

    return algorithms
