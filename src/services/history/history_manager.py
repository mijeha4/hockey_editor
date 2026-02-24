"""
History Manager — undo/redo stack with Command pattern.

Backwards-compatible API:
    execute_command(cmd), clear_history(), undo(), redo()

New API (aliases + extras):
    execute(cmd), clear(), push_command(cmd), mark_saved(),
    signals: state_changed, command_executed, command_undone, command_redone
"""

from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from services.history.command_interface import Command

_history_manager: Optional["HistoryManager"] = None


def get_history_manager() -> "HistoryManager":
    """Global singleton. All controllers share the same history."""
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
    return _history_manager


class HistoryManager(QObject):
    """
    Undo/Redo stack.

    Signals:
        state_changed        — any change to stacks
        command_executed(str) — description of executed command
        command_undone(str)   — description of undone command
        command_redone(str)   — description of redone command
    """

    state_changed = Signal()
    command_executed = Signal(str)
    command_undone = Signal(str)
    command_redone = Signal(str)

    DEFAULT_MAX_HISTORY = 200

    def __init__(
        self,
        max_history: int = DEFAULT_MAX_HISTORY,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_history = max_history
        self._batch_depth = 0
        self._batch_commands: List[Command] = []
        self._batch_description = ""
        self._modified_since_save = False

    # ─── Properties ──────────────────────────────────────────────────────

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    @property
    def undo_text(self) -> str:
        return self._undo_stack[-1].name if self._undo_stack else ""

    @property
    def redo_text(self) -> str:
        return self._redo_stack[-1].name if self._redo_stack else ""

    @property
    def undo_history(self) -> List[str]:
        """Descriptions from newest to oldest."""
        return [cmd.name for cmd in reversed(self._undo_stack)]

    @property
    def redo_history(self) -> List[str]:
        return [cmd.name for cmd in reversed(self._redo_stack)]

    @property
    def is_modified(self) -> bool:
        return self._modified_since_save

    @property
    def history_count(self) -> int:
        return len(self._undo_stack)

    # ─── Core: execute ───────────────────────────────────────────────────

    def execute_command(self, command: "Command") -> None:
        """Execute command and push to undo stack (primary API)."""
        command.execute()

        if self._batch_depth > 0:
            self._batch_commands.append(command)
            return

        self._push_undo(command)
        self._clear_redo()

        self._modified_since_save = True
        self.command_executed.emit(command.name)
        self.state_changed.emit()

    def execute(self, command: "Command") -> None:
        """Alias for execute_command."""
        self.execute_command(command)

    def push_command(self, command: "Command") -> None:
        """Push an already-executed command (no execute() call).

        Use when changes were applied directly (e.g. instance editor).
        """
        if self._batch_depth > 0:
            self._batch_commands.append(command)
            return

        self._push_undo(command)
        self._clear_redo()

        self._modified_since_save = True
        self.command_executed.emit(command.name)
        self.state_changed.emit()

    # ─── Core: undo / redo ───────────────────────────────────────────────

    def undo(self) -> Optional[str]:
        """Undo last command. Returns description or None."""
        if not self.can_undo:
            return None

        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)

        self._modified_since_save = True
        desc = command.name
        self.command_undone.emit(desc)
        self.state_changed.emit()
        return desc

    def redo(self) -> Optional[str]:
        """Redo last undone command. Returns description or None."""
        if not self.can_redo:
            return None

        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)

        self._modified_since_save = True
        desc = command.name
        self.command_redone.emit(desc)
        self.state_changed.emit()
        return desc

    # ─── Core: clear ─────────────────────────────────────────────────────

    def clear_history(self) -> None:
        """Clear all undo/redo history (primary API)."""
        for cmd in self._undo_stack:
            cmd.dispose()
        for cmd in self._redo_stack:
            cmd.dispose()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._modified_since_save = False
        self.state_changed.emit()

    def clear(self) -> None:
        """Alias for clear_history."""
        self.clear_history()

    # ─── Save tracking ───────────────────────────────────────────────────

    def mark_saved(self) -> None:
        """Mark current state as saved (clears modified flag)."""
        self._modified_since_save = False
        self.state_changed.emit()

    # ─── Batch operations ────────────────────────────────────────────────

    def begin_batch(self, description: str = "Batch operation") -> None:
        """Start a batch — all commands until end_batch are one undo step."""
        self._batch_depth += 1
        if self._batch_depth == 1:
            self._batch_commands = []
            self._batch_description = description

    def end_batch(self) -> None:
        """Finish batch and push as single compound command."""
        if self._batch_depth <= 0:
            return
        self._batch_depth -= 1

        if self._batch_depth == 0 and self._batch_commands:
            batch = _BatchCommand(
                self._batch_commands.copy(),
                self._batch_description,
            )
            self._push_undo(batch)
            self._clear_redo()
            self._batch_commands.clear()

            self._modified_since_save = True
            self.command_executed.emit(batch.name)
            self.state_changed.emit()

    # ─── Internals ───────────────────────────────────────────────────────

    def _push_undo(self, command) -> None:
        self._undo_stack.append(command)
        while len(self._undo_stack) > self._max_history:
            old = self._undo_stack.pop(0)
            old.dispose()

    def _clear_redo(self) -> None:
        for cmd in self._redo_stack:
            cmd.dispose()
        self._redo_stack.clear()


class _BatchCommand:
    """Compound command — atomic execute/undo of multiple sub-commands."""

    def __init__(self, commands: list, description: str):
        self._commands = commands
        self.description = description

    @property
    def name(self) -> str:
        return self.description

    def execute(self) -> None:
        for cmd in self._commands:
            cmd.execute()

    def undo(self) -> None:
        for cmd in reversed(self._commands):
            cmd.undo()

    def dispose(self) -> None:
        for cmd in self._commands:
            cmd.dispose()