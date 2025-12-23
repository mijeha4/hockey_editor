from abc import ABC, abstractmethod


class QUndoCommand(ABC):
    """Базовый класс для команд undo/redo."""

    def __init__(self):
        self.description = ""

    @abstractmethod
    def undo(self):
        """Отменить операцию."""
        pass

    @abstractmethod
    def redo(self):
        """Повторить операцию."""
        pass
