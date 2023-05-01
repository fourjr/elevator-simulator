from collections import deque
from dataclasses import dataclass
from typing import Any, Deque

from constants import ActionType


@dataclass
class Action:
    action_type: ActionType
    arg: Any = None


class ActionQueue:
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
