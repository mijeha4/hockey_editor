# utils/undo_redo.py
# Исправленная версия — поддерживает новую структуру Marker (event_name)

from PySide6.QtCore import QObject
from typing import List
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


class MarkerCommand(QUndoCommand):
    """Базовый класс для команд операций с маркерами."""

    def __init__(self, markers_list: List):
        super().__init__()
        self.markers = markers_list


class AddMarkerCommand(MarkerCommand):
    """Команда добавления маркера."""

    def __init__(self, markers_list: List, marker):
        super().__init__(markers_list)
        self.marker = marker
        # ИСПРАВЛЕНО: используется event_name вместо type.name
        self.description = f"Add {marker.event_name} marker"

    def undo(self):
        """Удалить маркер."""
        if self.marker in self.markers:
            self.markers.remove(self.marker)

    def redo(self):
        """Добавить маркер."""
        if self.marker not in self.markers:
            self.markers.append(self.marker)


class DeleteMarkerCommand(MarkerCommand):
    """Команда удаления маркера."""

    def __init__(self, markers_list: List, index: int):
        super().__init__(markers_list)
        self.index = index
        if 0 <= index < len(markers_list):
            self.marker = markers_list[index]
            # ИСПРАВЛЕНО: используется event_name вместо type.name
            self.description = f"Delete {self.marker.event_name} marker"
        else:
            self.marker = None
            self.description = "Delete marker"

    def undo(self):
        """Восстановить маркер."""
        if self.marker and self.marker not in self.markers:
            self.markers.insert(self.index, self.marker)

    def redo(self):
        """Удалить маркер."""
        if self.marker and self.marker in self.markers:
            self.markers.remove(self.marker)


class ModifyMarkerCommand(MarkerCommand):
    """Команда изменения маркера."""

    def __init__(self, markers_list: List, index: int, old_marker, new_marker):
        super().__init__(markers_list)
        self.index = index
        self.old_marker = old_marker
        self.new_marker = new_marker
        # ИСПРАВЛЕНО: используется event_name вместо type.name
        self.description = f"Modify {old_marker.event_name} marker"

    def undo(self):
        """Восстановить старый маркер."""
        if 0 <= self.index < len(self.markers):
            self.markers[self.index] = self.old_marker

    def redo(self):
        """Применить новый маркер."""
        if 0 <= self.index < len(self.markers):
            self.markers[self.index] = self.new_marker


class ClearMarkersCommand(MarkerCommand):
    """Команда очистки всех маркеров."""

    def __init__(self, markers_list: List):
        super().__init__(markers_list)
        self.saved_markers = markers_list.copy()
        self.description = "Clear all markers"

    def undo(self):
        """Восстановить все маркеры."""
        self.markers.clear()
        self.markers.extend(self.saved_markers)

    def redo(self):
        """Удалить все маркеры."""
        self.markers.clear()


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