import asyncio
from typing import List

from models import ElevatorManager, load_algorithms
from utils import Constants, LogLevel, LogOrigin, TestTimeoutError, NoManagerError
from web.backend.connection import WSConnection


class AsyncWebManager(ElevatorManager):
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
        self.ws_connection: WSConnection = None

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
            raise TestTimeoutError(self.name, n_iter, settings)

    def on_load_move(self, _):
        self.latest_load_move = self.algorithm.tick_count

    def start_simulation(self):
        self.log_message(
            LogOrigin.TEST,
            LogLevel.ERROR,
            f'{self.name=} START',
        )
        self._running = True
        task = asyncio.create_task(self.loop())
        self.loop.run_in_executor(None, task)
        # thread = threading.Thread(target=self.loop)
        # thread.start()

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


class AsyncioManagerPool:
    def __init__(self, min_managers: int, max_managers: int) -> None:
        """Creates a pool of managers"""
        self.managers: List[AsyncWebManager] = []
        for _ in range(min_managers):
            self.managers.append(AsyncWebManager())

        self.min_managers = min_managers
        self.max_managers = max_managers
        self.taken_managers = set()
        self.lock = asyncio.Lock()

    async def get(self) -> AsyncWebManager:
        """Gets a manager from the pool

        If no managers are available, a new one is created if the max_managers limit has not been reached
        """
        async with self.lock:
            m = [manager for manager in self.managers if manager.id not in self.taken_managers]
            if len(m) == 0:
                if len(self.managers) >= self.max_managers:
                    raise NoManagerError('No managers available')
                else:
                    take = AsyncWebManager()
                    self.managers.append(take)
            else:
                take = m[0]
            self.taken_managers.add(take.id)
            return take

    async def release(self, manager: AsyncWebManager) -> None:
        """Releases a manager back to the pool"""
        async with self.lock:
            self.taken_managers.remove(manager.id)
            if len(self.managers) > self.min_managers:
                manager.close()
                self.managers.remove(manager)

    def close(self) -> None:
        """Closes all managers"""
        for manager in self.managers:
            manager.close()
