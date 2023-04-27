import glob
import gzip
import importlib
import os
import pickle
from datetime import datetime

from errors import InvalidAlgorithm
from models import ElevatorAlgorithm


def load_algorithms() -> dict[str, ElevatorAlgorithm]:
    algorithms = {}
    for i in glob.iglob("algorithms/*.py"):
        module = importlib.import_module(i.replace(os.path.sep, ".")[:-3])
        if not hasattr(module, "__algorithm__"):
            raise InvalidAlgorithm(f"Algorithm in {module} is not defined")
        if not hasattr(module, "__name__"):
            raise InvalidAlgorithm(f"Name in {module} is not defined")

        algorithm = module.__algorithm__
        if not issubclass(algorithm, ElevatorAlgorithm):
            raise InvalidAlgorithm(
                f"Algorithm in {module} is not a subclass of ElevatorAlgorithm"
            )

        algorithm.name = module.__name__
        algorithms[algorithm.name] = algorithm

    return algorithms


def save_algorithm(algorithm, fn=None):
    dt = datetime.now().isoformat().replace(":", "-")
    if fn is None:
        fn = f"{dt}_{algorithm.name}.esi"

    if not os.path.isdir("exports"):
        os.mkdir("exports")

    fp = os.path.join("exports", fn)
    with open(fp, "wb") as f:
        f.write(
            f"fourjr/elevator-simulator {dt} fourjr/elevator-simulator\00\00".encode(
                "utf8"
            )
            + gzip.compress(pickle.dumps(algorithm))
            + f"\00\00fourjr/elevator-simulator {dt} fourjr/elevator-simulator".encode(
                "utf8"
            )
        )

    return fn

def split_array(a, n):
    """https://stackoverflow.com/a/2135920/8129786"""
    k, m = divmod(len(a), n)
    return (a[(i % len(a))*k+min(i % len(a), m):(i+1)*k+min((i % len(a))+1, m)] for i in range(n))
