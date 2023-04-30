import statistics
from dataclasses import dataclass, field
from typing import List


@dataclass
class GeneratedStats:
    values: List[float | int] = field(default_factory=list)

    def append(self, value: float | int):
        self.values.append(value)

    @property
    def mean(self):
        if len(self.values) == 0:
            return 0
        return statistics.mean(self.values)

    @property
    def median(self):
        if len(self.values) == 0:
            return 0
        return statistics.median(self.values)

    @property
    def minimum(self):
        if len(self.values) == 0:
            return 0
        return min(self.values)

    @property
    def maximum(self):
        if len(self.values) == 0:
            return 0
        return max(self.values)

    def __len__(self):
        return len(self.values)

    def __str__(self):
        return f'{self.minimum:.2f}/{self.mean:.2f}/{self.median:.2f}/{self.maximum:.2f}'

    def to_dict(self):
        return {
            'mean': self.mean,
            'median': self.median,
            'minimum': self.minimum,
            'maximum': self.maximum,
        }

    def __repr__(self) -> str:
        return f'<GeneratedStats size={len(self.values)}>'


@dataclass
class CombinedStats:
    stats: List[GeneratedStats | int] = field(default_factory=list)

    def append(self, stat: GeneratedStats):
        self.stats.append(stat)

    def extend(self, stats: List[GeneratedStats]):
        self.stats.extend(stats)

    @property
    def mean(self):
        if len(self.stats) == 0:
            return 0
        if isinstance(self.stats[0], int):
            return statistics.mean(self.stats)

        return statistics.mean([stat.mean for stat in self.stats])

    @property
    def median(self):
        if len(self.stats) == 0:
            return 0

        if isinstance(self.stats[0], int):
            return statistics.median(self.stats)

        return statistics.mean([stat.median for stat in self.stats])

    @property
    def minimum(self):
        if len(self.stats) == 0:
            return 0

        if isinstance(self.stats[0], int):
            return min(self.stats)

        return statistics.mean([stat.minimum for stat in self.stats])

    @property
    def maximum(self):
        if len(self.stats) == 0:
            return 0

        if isinstance(self.stats[0], int):
            return max(self.stats)

        return statistics.mean([stat.maximum for stat in self.stats])

    def __str__(self):
        return f'{self.minimum:.2f}/{self.mean:.2f}/{self.median:.2f}/{self.maximum:.2f}'

    def __or__(self, other: 'GeneratedStats') -> 'CombinedStats':
        """Combines another GeneratedStats object using the | operator"""
        if not isinstance(other, GeneratedStats):
            return super().__or__(other)

        return CombinedStats(self.stats + [other])

    def __len__(self):
        return len(self.stats)

    def to_dict(self):
        return {
            'mean': self.mean,
            'median': self.median,
            'minimum': self.minimum,
            'maximum': self.maximum,
        }


@dataclass
class SimulationStats:
    ticks: int
    algorithm_name: str
    wait_time: GeneratedStats
    time_in_lift: GeneratedStats
    occupancy: GeneratedStats

    def __str__(self) -> str:
        fmt_text = f'Tick: {self.ticks}\nAlgorithm: {self.algorithm_name}\n\n(MIN/MEAN/MED/MAX)\n\n'
        fmt_text += f'Wait Time: {self.wait_time}\n'
        fmt_text += f'Time in Lift: {self.time_in_lift}\n'
        fmt_text += f'Occupancy: {self.occupancy}'
        return fmt_text
