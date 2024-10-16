from __future__ import annotations
import asyncio
import itertools
import logging
import time
from typing import Callable, List, Tuple

import wx

from utils import _InfinitySentinel, run_async_or_sync
from models import ElevatorAlgorithm


class ElevatorManager:
    _id_iter = itertools.count()

    def __init__(
        self,
        parent,
        event: Callable,
        algorithm: 'ElevatorAlgorithm',
        *,
        gui: bool = True,
        log_func: Callable[[int, str], None] = None,
        sync: bool = True
    ):
        super().__init__()
        self.parent = parent
        self.event = event
        self.speed = 3
        self.algorithm: 'ElevatorAlgorithm' = algorithm(self)
        self.is_open = True
        self.gui = gui
        self.id = next(ElevatorManager._id_iter)
        self.sync = sync

        if log_func is None:
            self.WriteToLog = self.parent.WriteToLog
        else:
            self.WriteToLog = log_func

    @property
    def running(self):
        raise NotImplementedError

    def _on_loop(self):
        pass

    async def on_async_loop_exception(self, e: Exception):
        pass

    @property
    def loop(self):
        if self.sync:
            return self._sync_loop
        return self._asyncio_loop

    async def _asyncio_loop(self):
        try:
            while self.running and self.is_open:
                if self.algorithm.active:
                    self.algorithm.loop()
                    await run_async_or_sync(self._on_loop)

                    if self.algorithm.simulation_running:
                        # only append if there are things going on
                        for elevator in self.algorithm.elevators:
                            self.algorithm.occupancy.append((elevator.load / self.algorithm.max_load) * 100)
                    else:
                        self.set_active(False)
                        self.WriteToLog(logging.INFO, 'Simulation finished, pausing')
                        await run_async_or_sync(self.on_simulation_end)

                    self.send_event()

                if not isinstance(self.speed, _InfinitySentinel):
                    await asyncio.sleep(1 / self.speed)
                    # speed: 3 seconds per floor (1x)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await self.on_async_loop_exception(e)

    def _sync_loop(self):
        while self.running and self.is_open:
            if self.algorithm.active:
                self.algorithm.loop()
                self._on_loop()

                if self.algorithm.simulation_running:
                    # only append if there are things going on
                    for elevator in self.algorithm.elevators:
                        self.algorithm.occupancy.append((elevator.load / self.algorithm.max_load) * 100)
                else:
                    self.set_active(False)
                    self.WriteToLog(logging.INFO, 'Simulation finished, pausing')
                    self.algorithm.on_simulation_end()
                    self.on_simulation_end()

                self.send_event()

            if not isinstance(self.speed, _InfinitySentinel):
                time.sleep(1 / self.speed)
                # speed: 3 seconds per floor (1x)

    def send_event(self):
        """Sends an event to the server"""
        if self.gui is True:
            event = self.event(algorithm=self.algorithm, thread=self)
            wx.PostEvent(self.parent, event)

    def add_elevator(self, current_floor: int):
        ev = self.algorithm.create_elevator(current_floor)
        self.send_event()
        return ev

    def remove_elevator(self, elevator_id: str):
        self.algorithm.remove_elevator(elevator_id)
        self.send_event()

    def set_floors(self, floor_count: int):
        self.algorithm.floors = floor_count
        self.send_event()

    def set_speed(self, speed: int):
        self.speed = speed

    def close(self):
        self.is_open = False

    def add_passenger(self, initial: int, destination: int):
        load = self.algorithm.add_passenger(initial, destination)
        self.send_event()
        return load

    def add_passengers(self, passengers: List[Tuple[int, int]]):
        loads = []
        for initial, destination in passengers:
            loads.append(self.algorithm.add_passenger(initial, destination))
        self.send_event()
        return loads

    def set_algorithm(self, cls: 'ElevatorAlgorithm'):
        self.algorithm = cls(
            self,
            self.algorithm.floors,
            elevators=self.algorithm.elevators,
            loads=self.algorithm.loads,
        )
        self.send_event()

    def set_max_load(self, new_max_load: int):
        self.algorithm.max_load = new_max_load
        self.send_event()

    def reset(self, cls: 'ElevatorAlgorithm' = None):
        if cls is None:
            cls = self.algorithm.__class__
        self.algorithm = cls(self)
        self.send_event()

    def set_active(self, active: bool):
        self.algorithm.active = active

    def pause(self):
        self.set_active(False)

    def play(self):
        self.set_active(True)

    def toggle_active(self):
        self.set_active(not self.algorithm.active)
        self.send_event()

    def on_load_move(self, load: 'Load'):
        pass

    def on_elevator_move(self, elevator: 'Elevator'):
        pass

    def on_elevator_destination_change(self, elevator: 'Elevator', destination: int):
        pass

    def on_load_unload(self, load: 'Load', elevator: 'Elevator'):
        pass

    def on_load_load(self, load: 'Load', elevator: 'Elevator'):
        pass

    def on_simulation_end(self):
        """Runs when the simulation ends"""
        pass
