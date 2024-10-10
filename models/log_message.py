from dataclasses import dataclass


@dataclass
class LogMessage:
    """A log message object

    Attributes:
        level: int
            The level of the log message
        message: str
            The message to log
        tick: init
            The tick the message was logged
    """

    level: int
    message: str
    tick: int
