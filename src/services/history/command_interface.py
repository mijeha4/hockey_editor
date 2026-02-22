from __future__ import annotations

from abc import ABC, abstractmethod


class Command(ABC):
    """Base class for undoable commands.

    Contract:
        - execute() applies the change
        - undo() reverts the change
        - execute() may be called again after undo() (redo)
    """

    def __init__(self, description: str = ""):
        self.description = description

    @property
    def name(self) -> str:
        """Human-readable command name for UI/logs."""
        return self.description or self.__class__.__name__

    @abstractmethod
    def execute(self) -> None:
        pass

    @abstractmethod
    def undo(self) -> None:
        pass

    def dispose(self) -> None:
        """Optional cleanup when command is dropped from history."""
        # Override if command holds large buffers/resources
        pass