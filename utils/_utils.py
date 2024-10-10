import gzip
import logging
import os
import pickle
from datetime import datetime
from typing import Generator, Tuple

from web.backend.constants import Algorithms


def save_algorithm(algorithm, fn=None) -> str:
    """Exports the algorithm

    fn: Optional[str]
        File name to save as
        Default: {datetime}_{algorithm_name}.esi

    Returns: file name
    """
    dt = datetime.now().isoformat().replace(':', '-')
    if fn is None:
        fn = f'{dt}_{algorithm.name}.esi'

    if not os.path.isdir('exports'):
        os.mkdir('exports')

    fp = os.path.join('exports', fn)
    with open(fp, 'wb') as f:
        f.write(
            f'fourjr/elevator-simulator {dt} fourjr/elevator-simulator\00\00'.encode('utf8')
            + gzip.compress(pickle.dumps(algorithm))
            + f'\00\00fourjr/elevator-simulator {dt} fourjr/elevator-simulator'.encode('utf8')
        )

    return fn


def split_array(a, n) -> Generator[Tuple[int], None, None]:
    """https://stackoverflow.com/a/2135920/8129786"""
    k, m = divmod(len(a), n)
    return (a[(i % len(a)) * k + min(i % len(a), m): (i + 1) * k + min((i % len(a)) + 1, m)] for i in range(n))


def jq_join_timeout(jq, timeout) -> None:
    """Joins a JoinableQueue with a given timeout

    Raises TimeoutError if the timeout is reached
        and there are still unfinished tasks
    """
    with jq._cond:
        if not jq._unfinished_tasks._semlock._is_zero():
            if not jq._cond.wait(timeout=timeout):
                raise TimeoutError('jq_join_timeout timed out')


def i2b(num: int) -> bytes:
    """Converts an integer to 2 bytes (little endian)"""
    return int(num).to_bytes(2, byteorder='little')


def b2i(data: bytes) -> int:
    """Converts 4 bytes to an integer (little endian)"""
    return int.from_bytes(data, byteorder='little')


def algo_to_enum(algo) -> int:
    """Converts an algorithm to an enum"""
    return Algorithms[algo.name.replace(' ', '_')]


def log_levels():
    """Returns a list of log levels"""
    return {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }


def get_log_level(name) -> str:
    """Returns the level int from name"""
    return log_levels()[name]


def get_log_name(level) -> str:
    """Returns the name from the level int"""
    return {v: k for k, v in log_levels().items()}[level]
