import multiprocessing as mp
import queue
from datetime import datetime
from typing import List

from constants import LogLevel, LogOrigin
from suite import TestSuiteConsumer
from utils import save_algorithm


class BackgroundProcess(mp.Process):
    def __init__(
        self,
        in_queue,
        out_queue,
        error_queue,
        export_queue,
        log_queue,
        consumers: List['TestSuiteConsumer'],
        close_event,
        log_levels,
    ):
        super().__init__()
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.error_queue = error_queue
        self.export_queue = export_queue
        self.log_queue = log_queue
        self.consumers = consumers
        self.close_event = close_event
        self.log_levels = log_levels

    def is_closed(self):
        return self.close_event.is_set()

    def run(self):
        try:
            while not self.is_closed():
                while not self.is_closed():
                    try:
                        name, e = self.error_queue.get(timeout=0.01)
                    except queue.Empty:
                        break
                    else:
                        del self.consumers[name]
                        consumer = TestSuiteConsumer(
                            self.in_queue,
                            self.out_queue,
                            self.error_queue,
                            self.export_queue,
                            self.log_queue,
                            self.log_levels,
                        )
                        consumer.start()
                        self.consumers[consumer.name] = consumer

                        self.log_queue.put(
                            (LogOrigin.ERROR_HANDLER, LogLevel.INFO, f'{name} died, restarting as {consumer.name}')
                        )
                        self.error_queue.task_done()

                if self.export_queue is not None:
                    while not self.is_closed():
                        try:
                            name, algo = self.export_queue.get(timeout=0.01)
                        except queue.Empty:
                            break
                        else:
                            dt = datetime.now().isoformat().replace(':', '-')
                            fn = f'{dt}_{name}.esi'
                            save_algorithm(algo, fn)
                            self.log_queue.put(
                                (LogOrigin.FILE_HANDLER, LogLevel.TRACE, f'{name} exported to {fn}')
                            )
                            self.export_queue.task_done()

                while not self.is_closed():
                    try:
                        origin, level, message = self.log_queue.get(timeout=0.01)
                    except queue.Empty:
                        break
                    else:
                        if level >= self.log_levels[origin]:
                            print(f'[{origin.name}] [{level.name[0]}] {message}')

                        self.log_queue.task_done()

        except KeyboardInterrupt:
            return
