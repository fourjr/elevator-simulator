import copy
import multiprocessing as mp
import random
import traceback

from constants import Constants, LogLevel, LogOrigin
from errors import TestTimeout
from models import ElevatorManager
from utils import load_algorithms


class TestSuiteConsumer(ElevatorManager, mp.Process):
    def __init__(self, in_queue, out_queue, error_queue, export_queue, log_queue, log_levels):
        self.algorithms = load_algorithms()
        super().__init__(
            self,
            None,
            self.algorithms[Constants.DEFAULT_ALGORITHM],
            gui=False,
            log_func=self.log_message_simulation,
        )
        self._running = False
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.error_queue = error_queue
        self.export_queue = export_queue
        self.log_queue = log_queue
        self.log_levels = log_levels

        self._process = mp.Process(target=self.process_loop, daemon=True)

        self.name = self._process.name
        self.latest_load_move = 0
        self.previous_loads = []
        self.current_simulation = None

    @property
    def running(self):
        return self._running

    def start(self):
        self._process.start()

    def close(self):
        self._process.terminate()
        self._process.join()
        self._process.close()
        super().close()

    def process_loop(self):
        try:
            while True:
                n_iter, settings = self.in_queue.get()

                self.current_simulation = (n_iter, settings)

                algo = self.algorithms[settings.algorithm_name]
                algo.name = settings.algorithm_name
                self.reset(algo)
                self.algorithm.rnd = random.Random((settings.seed + n_iter) % 2 ** 32)

                self.set_speed(settings.speed)
                self.set_floors(settings.floors)
                self.set_max_load(settings.max_load)

                settings.init_passengers(self.algorithm.rnd)

                elevator_floors = []
                for _ in range(settings.num_elevators):
                    elevator_floors.append(self.algorithm.rnd.randint(1, settings.floors))

                for floor in elevator_floors:
                    self.add_elevator(floor)

                for load in settings.loads:
                    self.algorithm.add_load(load)

                if settings.init_function is not None:
                    settings.init_function(self.algorithm)

                # save
                if self.export_queue is not None:
                    name = f'{settings.name}_{settings.algorithm_name}_{n_iter}'
                    self.export_queue.put((name, copy.deepcopy(self.algorithm)))

                self.active = True
                self.log_message(
                    LogOrigin.TEST,
                    LogLevel.TRACE,
                    f'{self.name} START SIMULATION: {n_iter=} {settings.name=} {settings.algorithm_name=}',
                )

                try:
                    self.start_simulation()
                except TestTimeout as e:
                    # continue with next simulation
                    self.out_queue.put(((n_iter, settings), e))
                    self.log_message(
                        LogOrigin.TEST,
                        LogLevel.WARNING,
                        f'{self.name} SKIP SIMULATION (TIMEOUT): {n_iter=} {settings.name=} {settings.algorithm_name=}',
                    )
                else:
                    self.log_message(
                        LogOrigin.TEST,
                        LogLevel.TRACE,
                        f'{self.name} END SIMULATION: {n_iter=} {settings.name=}  {settings.algorithm_name=}',
                    )
                    self.out_queue.put(((n_iter, settings), self.algorithm.stats))

                self.in_queue.task_done()

        except KeyboardInterrupt:
            return
        except Exception as e:
            # mark as done although errored
            self.in_queue.task_done()

            # need to format first as pickle will remove the traceback
            e.formatted_exception = traceback.format_exc().strip()

            if self.current_simulation is not None:
                n_iter, settings = self.current_simulation
                self.log_message(
                    LogOrigin.TEST,
                    LogLevel.ERROR,
                    f'{self.name} ERROR SIMULATION: {n_iter=} {settings.name=} {settings.algorithm_name=}\n\n{e.formatted_exception}',
                )
            else:
                self.log_message(
                    LogOrigin.TEST,
                    LogLevel.ERROR,
                    f'{self.name} ERROR SIMULATION\n\n{e.formatted_exception}',
                )

            self.out_queue.put(((n_iter, settings), e))
            self.error_queue.put((self.name, e))

    def on_tick(self):
        if self.running is True and self.algorithm.simulation_running is False:
            self.end_simulation()

        # frozen loads
        if self.algorithm.tick_count - self.latest_load_move > 500:
            self.end_simulation()
            n_iter, settings = self.current_simulation
            self.log_message(
                LogOrigin.TEST,
                LogLevel.ERROR,
                f'{self.name=} TIMEOUT: {n_iter=} {settings.name=} {settings.algorithm_name=}',
            )
            raise TestTimeout(self.name, n_iter, settings)

    def on_load_move(self, _):
        self.latest_load_move = self.algorithm.tick_count

    def start_simulation(self):
        self._running = True
        self.loop()

    def end_simulation(self):
        self._running = False

    def log_message_simulation(self, level, message):
        self.log_message(LogOrigin.SIMULATION, level, message)

    def log_message(self, origin, level, message):
        if level >= self.log_levels[origin]:
            self.log_queue.put((origin, level, message))

    def __getstate__(self):
        obj = self.__dict__.copy()
        del obj['_process']
        return obj
