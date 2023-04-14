import statistics
from typing import List


class Unicode:
    UP = "\u2191"
    DOWN = "\u2193"
    ARROW = "\u2192"


class Constants:
    DEFAULT_ALGORITHM = "Knuth"


def generate_stats(values: List[int | float]):
    if len(values) == 0:
        values = [0]

    vals = (
        min(values),
        statistics.mean(values),
        statistics.median(values),
        max(values)
    )
    return f'{vals[0]:.2f}/{vals[1]:.2f}/{vals[2]:.2f}/{vals[3]:.2f}'
