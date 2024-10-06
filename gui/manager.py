import threading
from typing import Callable

from models import ElevatorManager


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
