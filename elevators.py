import threading
import time
import wx
from managers import ElevatorManagerRandom


class ElevatorManagerThread(threading.Thread):
    def __init__(self, window, event):
        self.window = window
        self.event = event
        self.speed = 15
        super().__init__()
        self.manager = ElevatorManagerRandom(10)
        self.manager.create_elevator()
        self.start()


    def run(self):
        while self.is_alive():
            self.manager.cycle()
            self.send_event()
            time.sleep(15 * (1/self.speed))
            # thread delay is 
            # speed: 15 seconds per floor

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

