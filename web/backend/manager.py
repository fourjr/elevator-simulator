import asyncio
import logging
from typing import List

from models import ElevatorManager, load_algorithms
from utils import Constants, NoManagerError
from web.backend.connection import WSConnection
from web.backend.constants import GameStateUpdate, GameUpdateType, OpCode
from web.backend.packet import ServerPacket


logger = logging.getLogger('__main__.' + __name__)


class AsyncWebManager(ElevatorManager):
    def __init__(self):
        self.algorithms = load_algorithms()
        super().__init__(
            self,
            None,
            self.algorithms[Constants.DEFAULT_ALGORITHM],
            gui=False,
            log_func=self.log_message_web,
            sync=False
        )
        self.ws_connection: WSConnection = None

        self._running = False
        self.latest_load_move = 0
        self.previous_loads = []
        self.diff_events = []
        self._loop_task = None

    async def set_running(self, value):
        self._running = value
        if value:
            self._loop_task = asyncio.create_task(self.loop())
        else:
            try:
                await asyncio.wait_for(self._loop_task, timeout=0.5)  # try to gracefully end the loop
            except asyncio.TimeoutError:
                self._loop_task.cancel()

            self._loop_task = None

    def on_elevator_move(self, elevator: 'Elevator'):
        self.diff_events.append(GameStateUpdate(GameUpdateType.ELEVATOR_MOVE, elevator.id, elevator.current_floor))

    def on_elevator_destination_change(self, elevator: 'Elevator', destination: int):
        if destination is None:
            return
        self.diff_events.append(GameStateUpdate(GameUpdateType.ELEVATOR_DESTINATION, elevator.id, destination))

    def on_load_unload(self, load: 'Load', elevator: 'Elevator'):
        self.diff_events.append(GameStateUpdate(GameUpdateType.LOAD_UNLOAD, elevator.id, load.id))

    def on_load_load(self, load: 'Load', elevator: 'Elevator'):
        self.diff_events.append(GameStateUpdate(GameUpdateType.LOAD_LOAD, elevator.id, load.id))

    async def on_loop_tick_end(self):
        if self.ws_connection is not None:
            flattened_data = [self.algorithm.tick_count, len(self.diff_events)] + [x for event in self.diff_events for x in event.flatten()]
            await ServerPacket(OpCode.GAME_UPDATE_STATE, flattened_data).send(self.ws_connection.protocol)
            self.diff_events = []
        else:
            raise ValueError('No connection to send events to')

    @property
    def running(self):
        return self._running

    @property
    def name(self):
        return None

    def log_message_web(self, level, message):
        logger.log(level, message)

    def close(self):
        if self._loop_task is not None:
            self._loop_task.cancel()
        return super().close()


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
            await take.set_running(True)
            return take

    async def release(self, manager: AsyncWebManager) -> None:
        """Releases a manager back to the pool"""
        async with self.lock:
            self.taken_managers.remove(manager.id)
            if len(self.managers) > self.min_managers:
                manager.close()
                self.managers.remove(manager)
            else:
                await manager.set_running(False)

    def close(self) -> None:
        """Closes all managers"""
        for manager in self.managers:
            manager.close()
