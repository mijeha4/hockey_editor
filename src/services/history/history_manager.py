from typing import List
from .command_interface import Command


class HistoryManager:
    """Менеджер истории команд для undo/redo."""

    def __init__(self, max_history: int = 50):
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        self.max_history = max_history

    def execute_command(self, command: Command):
        """Выполнить команду и добавить в историю."""
        command.execute()
        self.undo_stack.append(command)

        # Очистить redo стек при новом действии
        self.redo_stack.clear()

        # Ограничить размер истории
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)

    def undo(self):
        """Отменить последнюю команду."""
        if not self.can_undo():
            return

        command = self.undo_stack.pop()
        command.undo()
        self.redo_stack.append(command)

    def redo(self):
        """Повторить отменённую команду."""
        if not self.can_redo():
            return

        command = self.redo_stack.pop()
        command.execute()
        self.undo_stack.append(command)

    def can_undo(self) -> bool:
        """Проверить, можно ли отменить."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Проверить, можно ли повторить."""
        return len(self.redo_stack) > 0

    def clear_history(self):
        """Очистить всю историю."""
        self.undo_stack.clear()
        self.redo_stack.clear()
