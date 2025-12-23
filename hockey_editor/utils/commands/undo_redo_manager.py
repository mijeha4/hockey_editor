from PySide6.QtCore import QObject
from typing import List
from .undo_command import QUndoCommand


class UndoRedoManager(QObject):
    """Менеджер undo/redo операций."""

    def __init__(self, max_history: int = 50):
        super().__init__()
        self.history: List[QUndoCommand] = []
        self.current_index = -1
        self.max_history = max_history

    def push_command(self, command: QUndoCommand):
        """Добавить команду в историю."""
        # Удалить все команды после текущей позиции (если мы делали undo, а потом новое действие)
        self.history = self.history[:self.current_index + 1]

        # Добавить новую команду
        self.history.append(command)
        self.current_index += 1

        # Выполнить команду (как в стандартном Qt QUndoStack)
        command.redo()

        # Ограничить размер истории
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.current_index -= 1

    def undo(self):
        """Отменить последнюю операцию."""
        if self.can_undo():
            command = self.history[self.current_index]
            command.undo()
            self.current_index -= 1

    def redo(self):
        """Повторить последнюю отменённую операцию."""
        if self.can_redo():
            self.current_index += 1
            command = self.history[self.current_index]
            command.redo()

    def can_undo(self) -> bool:
        """Проверить, можно ли отменить."""
        return self.current_index >= 0

    def can_redo(self) -> bool:
        """Проверить, можно ли повторить."""
        return self.current_index < len(self.history) - 1

    def clear_history(self):
        """Очистить историю команд."""
        self.history.clear()
        self.current_index = -1
