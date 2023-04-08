import threading
import time
import wx
from managers import ElevatorManagerRandom

class ElevatorManagerThread(threading.Thread):
    def __init__(self, window, event):
        super().__init__()
        self.window = window
        self.event = event
        self.speed = 3
        self.manager = ElevatorManagerRandom(self, 10)
        self.active = False
        self.is_open = True
        self.tick_count = 0
        self.start()

    def run(self):
        while self.is_alive() and self.is_open:
            if self.active:
                self.manager.cycle()
                self.tick_count += 1
                self.send_event()

            time.sleep(3 * (1/self.speed))

            # speed: 3 seconds per floor (1x)

    def send_event(self):
        event = self.event(manager=self.manager, thread=self)
        wx.PostEvent(self.window, event)

    def add_elevator(self, current_floor, attributes=None):
        self.manager.create_elevator(current_floor, attributes)
        self.send_event()

    def set_floors(self, floors):
        self.manager.floors = floors
        self.send_event()

    def set_speed(self, speed):
        self.speed = speed

    def close(self):
        self.is_open = False

    def add_passenger(self, initial, destination):
        self.manager.add_passenger(initial, destination)
        self.send_event()

    def set_manager(self, cls):
        self.manager = cls(self, self.manager.floors, elevators=self.manager.elevators, loads=self.manager.loads)
        self.send_event()

    def set_max_load(self, new_max_load):
        self.manager.max_load = new_max_load
        self.send_event()

    def reset(self, cls):
        self.manager = cls(self, self.manager.floors)
        self.send_event()
