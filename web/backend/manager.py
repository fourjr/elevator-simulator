import random
import threading
import traceback
import multiprocessing as mp

from constants import Constants, LogLevel, LogOrigin
from errors import TestTimeout
from models import ElevatorManager
from utils import load_algorithms


class WebManager(ElevatorManager):
    def __init__(self):
        self.algorithms = load_algorithms()
        super().__init__(
            self,
            None,
            self.algorithms[Constants.DEFAULT_ALGORITHM],
            gui=False,
            log_func=self.log_message_simulation,
        )
        self._running = False
        self.server = None

        self.latest_load_move = 0
        self.previous_loads = []

    @property
    def running(self):
        return self._running

    @property
    def name(self):
        return None

    def _on_loop(self):
        # frozen loads
        if self.algorithm.tick_count - self.latest_load_move > 500:
            self.end_test_simulation()
            n_iter, settings = self.current_simulation
            self.log_message(
                LogOrigin.TEST,
                LogLevel.ERROR,
                f'{self.name=} TIMEOUT',
            )
            raise TestTimeout(self.name, n_iter, settings)

    def on_load_move(self, _):
        self.latest_load_move = self.algorithm.tick_count

    def start_simulation(self):
        self.log_message(
            LogOrigin.TEST,
            LogLevel.ERROR,
            f'{self.name=} START',
        )
        self._running = True
        thread = threading.Thread(target=self.loop)
        thread.start()

        # self.loop()

    def on_simulation_end(self):
        self.end_test_simulation()

    def end_test_simulation(self):
        self._running = False

    def log_message_simulation(self, level, message):
        self.log_message(LogOrigin.SIMULATION, level, message)

    def log_message(self, origin, level, message):
        fmt = f'[{origin.name}] [{level.name[0]}] {message}'
        print(fmt)
        self.ws_info[0].log(self.ws_info[1], fmt)


class ManagerPool:
    def __init__(self, mp_manager: mp.Manager, managers=None) -> None:
        self.managers = managers or []
        self.taken_managers = set()
        self.lock = mp_manager.Lock()

    def get(self):
        with self.lock:
            m = [manager for manager in self.managers if manager.id not in self.taken_managers]
            if len(m) == 0:
                raise ValueError('No managers available')
            take = m[0]
            self.taken_managers.add(take.id)
            return take

    def release(self, manager):
        with self.lock:
            self.taken_managers.remove(manager.id)

    def append(self, manager):
        with self.lock:
            self.managers.append(manager)

    def close(self):
        for manager in self.managers:
            manager.close()


def run_loop(args):
    (n_iter, settings), managers = args
    manager = managers.get()
    try:
        manager.current_simulation = (n_iter, settings)

        algo = manager.algorithms[settings.algorithm_name]
        algo.name = settings.algorithm_name
        manager.reset(algo)
        manager.algorithm.rnd = random.Random((settings.seed + n_iter) % 2 ** 32)

        manager.set_speed(settings.speed)
        manager.set_floors(settings.floors)
        manager.set_max_load(settings.max_load)

        settings.init_passengers(manager.algorithm.rnd)

        elevator_floors = []
        for _ in range(settings.num_elevators):
            elevator_floors.append(manager.algorithm.rnd.randint(1, settings.floors))

        for floor in elevator_floors:
            manager.add_elevator(floor)

        for load in settings.loads:
            manager.algorithm.add_load(load)

        if settings.init_function is not None:
            settings.init_function(manager.algorithm)

        # save
        if manager.export_queue is not None:
            name = f'{settings.name}_{settings.algorithm_name}_{n_iter}'
            manager.export_queue.put((name, manager.algorithm.copy()))

        manager.set_active(True)
        manager.log_message(
            LogOrigin.TEST,
            LogLevel.TRACE,
            f'{manager.name} START SIMULATION',
        )

        try:
            manager.start_simulation()
        except TestTimeout as e:
            # continue with next simulation
            manager.log_message(
                LogOrigin.TEST,
                LogLevel.WARNING,
                f'{manager.name} SKIP SIMULATION (TIMEOUT)',
            )
            return ((n_iter, settings), e)
        else:
            manager.log_message(
                LogOrigin.TEST,
                LogLevel.TRACE,
                f'{manager.name} END SIMULATION',
            )
            return ((n_iter, settings), manager.algorithm.stats)

    except KeyboardInterrupt:
        return
    except Exception as e:
        # need to format first as pickle will remove the traceback
        e.formatted_exception = traceback.format_exc().strip()

        manager.log_message(
            LogOrigin.TEST,
            LogLevel.ERROR,
            f'{manager.name} ERROR SIMULATION\n\n{e.formatted_exception}',
        )

        return ((n_iter, settings), e)
    finally:
        managers.release(manager)
