from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from .command_interface import Command


class HistoryManager(QObject):
    """Менеджер истории команд для undo/redo."""

    history_changed = Signal(bool, bool)  # can_undo, can_redo
    command_executed = Signal(str)        # command description/name (optional)
    command_undone = Signal(str)          # optional
    command_redone = Signal(str)          # optional
    error = Signal(str)                   # optional

    def __init__(self, max_history: int = 50, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.undo_stack: List[Command] = []
        self.redo_stack: List[Command] = []
        self.max_history = max_history

    def execute_command(self, command: Command) -> bool:
        """Выполнить команду и добавить в историю.

        Returns:
            True if executed successfully.
        """
        try:
            command.execute()
        except Exception as e:
            self.error.emit(f"Command execute failed: {e}")
            return False

        self.undo_stack.append(command)
        self.redo_stack.clear()

        if len(self.undo_stack) > self.max_history:
            dropped = self.undo_stack.pop(0)
            # Optional: if Command has dispose/cleanup
            if hasattr(dropped, "dispose"):
                try:
                    dropped.dispose()
                except Exception:
                    pass

        self.command_executed.emit(getattr(command, "name", command.__class__.__name__))
        self._emit_state()
        return True

    def undo(self) -> bool:
        """Отменить последнюю команду."""
        if not self.can_undo():
            return False

        command = self.undo_stack.pop()
        try:
            command.undo()
        except Exception as e:
            self.error.emit(f"Command undo failed: {e}")
            # Push it back to keep consistent state
            self.undo_stack.append(command)
            self._emit_state()
            return False

        self.redo_stack.append(command)
        self.command_undone.emit(getattr(command, "name", command.__class__.__name__))
        self._emit_state()
        return True

    def redo(self) -> bool:
        """Повторить отменённую команду."""
        if not self.can_redo():
            return False

        command = self.redo_stack.pop()
        try:
            command.execute()
        except Exception as e:
            self.error.emit(f"Command redo failed: {e}")
            # Push it back
            self.redo_stack.append(command)
            self._emit_state()
            return False

        self.undo_stack.append(command)
        self.command_redone.emit(getattr(command, "name", command.__class__.__name__))
        self._emit_state()
        return True

    def can_undo(self) -> bool:
        return bool(self.undo_stack)

    def can_redo(self) -> bool:
        return bool(self.redo_stack)

    def clear_history(self) -> None:
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._emit_state()

    def _emit_state(self) -> None:
        self.history_changed.emit(self.can_undo(), self.can_redo())