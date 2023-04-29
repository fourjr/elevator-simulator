from __future__ import annotations
import threading
import time
from typing import Callable, List, Tuple

import wx

from constants import Infinity


class ElevatorManager:
    def __init__(
        self,
        parent,
        event: Callable,
        algorithm: 'ElevatorAlgorithm',
        *,
        gui: bool = True,
        log_func: Callable = None,
    ):
        super().__init__()
        self.parent = parent
        self.event = event
        self.speed = 3
        self.algorithm: 'ElevatorAlgorithm' = algorithm(self)
        self.active = False
        self.is_open = True
        self.gui = gui

        if log_func is None:
            self.WriteToLog = self.parent.WriteToLog
        else:
            self.WriteToLog = log_func

    @property
    def running(self):
        raise NotImplementedError

    def on_tick(self):
        pass

    def loop(self):
        while self.running and self.is_open:
            if self.active:
                self.algorithm.cycle()
                self.send_event()
                self.on_tick()

                if self.algorithm.simulation_running:
                    # only append if there are things going on
                    for elevator in self.algorithm.elevators:
                        self.algorithm.occupancy.append((elevator.load / self.algorithm.max_load) * 100)

            if self.speed != Infinity:
                time.sleep(3 * (1 / self.speed))

            # speed: 3 seconds per floor (1x)

    def send_event(self):
        if self.gui is True:
            event = self.event(algorithm=self.algorithm, thread=self)
            wx.PostEvent(self.parent, event)

    def add_elevator(self, current_floor: int, attributes=None):
        self.algorithm.create_elevator(current_floor, attributes)
        self.send_event()

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
        self.algorithm.add_passenger(initial, destination)
        self.send_event()

    def add_passengers(self, passengers: List[Tuple[int, int]]):
        for initial, destination in passengers:
            self.algorithm.add_passenger(initial, destination)
        self.send_event()

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

    def reset(self, cls: 'ElevatorAlgorithm'):
        self.algorithm = cls(self)
        self.send_event()

    def set_active(self, active: bool):
        self.active = active

    def pause(self):
        self.set_active(False)

    def play(self):
        self.set_active(True)

    def on_load_move(self, load: 'Load'):
        pass


class ElevatorManagerThread(ElevatorManager, threading.Thread):
    def __init__(self, parent, event: Callable, algorithm: 'ElevatorAlgorithm', *, gui: bool = True):
        ElevatorManager.__init__(self, parent, event, algorithm, gui=gui)
        threading.Thread.__init__(self)
        self.start()

    def run(self):
        self.loop()

    @property
    def running(self):
        return self.is_alive()
