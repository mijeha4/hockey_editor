from abc import ABC, abstractmethod


class Command(ABC):
    """Абстрактный базовый класс для команд."""

    def __init__(self, description: str = ""):
        self.description = description

    @abstractmethod
    def execute(self):
        """Выполнить команду."""
        pass

    @abstractmethod
    def undo(self):
        """Отменить команду."""
        pass
