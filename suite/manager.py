import random
import traceback
import multiprocessing as mp

from utils import Constants, LogLevel, LogOrigin
from utils import TestTimeoutError
from models import ElevatorManager
from utils import load_algorithms


class TestSuiteManager(ElevatorManager):
    def __init__(self, export_queue, log_queue, log_levels):
        self.algorithms = load_algorithms()
        super().__init__(
            self,
            None,
            self.algorithms[Constants.DEFAULT_ALGORITHM],
            gui=False,
            log_func=self.log_message_simulation,
        )
        self._running = False
        self.export_queue = export_queue
        self.log_queue = log_queue
        self.log_levels = log_levels

        self.latest_load_move = 0
        self.previous_loads = []
        self.current_simulation = None

    @property
    def running(self):
        return self._running

    @property
    def name(self):
        if self.current_simulation is not None:
            n_iter, settings = self.current_simulation
            return f'{settings.name}_{settings.algorithm_name}_{n_iter}'
        else:
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
            raise TestTimeoutError(self.name, n_iter, settings)

        if self.algorithm.active:
            if self.current_simulation[1].on_tick is not None:
                self.current_simulation[1].on_tick(self.algorithm)

    def on_load_move(self, _):
        self.latest_load_move = self.algorithm.tick_count

    def start_simulation(self):
        self._running = True
        self.loop()

    def on_simulation_end(self):
        self.end_test_simulation()

    def end_test_simulation(self):
        self._running = False

    def log_message_simulation(self, level, message):
        self.log_message(LogOrigin.SIMULATION, level, message)

    def log_message(self, origin, level, message):
        if level >= self.log_levels[origin]:
            self.log_queue.put((origin, level, message))


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
    (n_iter, settings), consumers = args
    manager = consumers.get()
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
        except TestTimeoutError as e:
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
        consumers.release(manager)
