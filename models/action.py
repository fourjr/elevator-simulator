from collections import deque
from dataclasses import dataclass
from typing import Any, Deque

from constants import ActionType


@dataclass
class Action:
    action_type: ActionType
    argument: Any = None


class ActionQueue:
    """A queue of actions to be performed by the elevator"""

    def __init__(self):
        self.actions: Deque[Action] = deque()

    def get(self):
        try:
            return self.actions.popleft()
        except IndexError:
            return Action(ActionType.RUN_CYCLE)

    def add(self, action: Action):
        self.actions.append(action)

    def tick(self, count=1):
        for _ in range(count):
            self.actions.append(Action(ActionType.ADD_TICK))

    def open_door(self):
        self.tick(3)

    def close_door(self):
        self.tick(3)

    def copy(self):
        new_queue = ActionQueue()
        new_queue.actions = self.actions.copy()
        return new_queue
