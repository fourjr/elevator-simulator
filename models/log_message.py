from dataclasses import dataclass

from constants import LogLevel


@dataclass
class LogMessage:
    """A log message object

    Attributes:
        level: LogLevel
            The level of the log message
        message: str
            The message to log
        tick: init
            The tick the message was logged
    """

    level: LogLevel
    message: str
    tick: int
