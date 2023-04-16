import threading
import time
from typing import Callable, List, Tuple
import wx

from models import ElevatorManager


class ElevatorManagerThread(threading.Thread):
    def __init__(self, parent, event: Callable, manager: ElevatorManager, *, gui: bool=True):
        super().__init__()
        self.parent = parent
        self.event = event
        self.speed = 3
        self.manager: ElevatorManager = manager(self, 10)
        self.active = False
        self.is_open = True
        self.current_tick = 0
        self.gui = gui
        self.start()

    def on_tick(self):
        pass

    def run(self):
        while self.is_alive() and self.is_open:
            if self.active:
                self.manager.cycle()
                self.current_tick += 1
                self.send_event()
                self.on_tick()

                if self.manager.simulation_running:
                    # only append if there are things going on
                    for elevator in self.manager.elevators:
                        self.manager.occupancy.append(
                            (elevator.load / self.manager.max_load) * 100
                        )

            time.sleep(3 * (1 / self.speed))

            # speed: 3 seconds per floor (1x)

    def send_event(self):
        event = self.event(manager=self.manager, thread=self)
        if self.gui is True:
            wx.PostEvent(self.parent, event)

    def add_elevator(self, current_floor: int, attributes=None):
        self.manager.create_elevator(current_floor, attributes)
        self.send_event()

    def remove_elevator(self, elevator_id: str):
        self.manager.remove_elevator(elevator_id)
        self.send_event()

    def set_floors(self, floor_count: int):
        self.manager.floors = floor_count
        self.send_event()

    def set_speed(self, speed: int):
        self.speed = speed

    def close(self):
        self.is_open = False

    def add_passenger(self, initial: int, destination: int):
        self.manager.add_passenger(initial, destination)
        self.send_event()

    def add_passengers(self, passengers: List[Tuple[int, int]]):
        for initial, destination in passengers:
            self.manager.add_passenger(initial, destination)
        self.send_event()

    def set_manager(self, cls: ElevatorManager):
        self.manager = cls(
            self,
            self.manager.floors,
            elevators=self.manager.elevators,
            loads=self.manager.loads,
        )
        self.send_event()

    def set_max_load(self, new_max_load: int):
        self.manager.max_load = new_max_load
        self.send_event()

    def reset(self, cls: ElevatorManager):
        self.current_tick = 0
        self.manager = cls(self, self.manager.floors)
        self.send_event()

    def set_active(self, active: bool):
        self.active = active

    def pause(self):
        self.set_active(False)

    def play(self):
        self.set_active(True)
