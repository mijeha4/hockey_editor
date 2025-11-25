"""
Undo/Redo System - QUndoStack с командами для всех операций.
"""

from PySide6.QtGui import QUndoStack, QUndoCommand
from PySide6.QtCore import Signal, QObject
from typing import Optional, List
from ..models.marker import Marker, EventType


class MarkerCommand(QUndoCommand):
    """Базовый класс для команд операций с маркерами."""
    
    def __init__(self, description: str):
        super().__init__(description)


class AddMarkerCommand(MarkerCommand):
    """Команда добавления маркера."""
    
    def __init__(self, markers_list: List[Marker], marker: Marker):
        super().__init__(f"Add {marker.type.name} marker")
        self.markers_list = markers_list
        self.marker = marker.copy() if hasattr(marker, 'copy') else marker

    def redo(self):
        """Добавить маркер."""
        self.markers_list.append(self.marker)

    def undo(self):
        """Удалить маркер."""
        if self.marker in self.markers_list:
            self.markers_list.remove(self.marker)


class DeleteMarkerCommand(MarkerCommand):
    """Команда удаления маркера."""
    
    def __init__(self, markers_list: List[Marker], index: int):
        super().__init__("Delete marker")
        self.markers_list = markers_list
        self.index = index
        self.marker = markers_list[index].copy() if hasattr(markers_list[index], 'copy') else markers_list[index]

    def redo(self):
        """Удалить маркер."""
        if self.index < len(self.markers_list):
            self.markers_list.pop(self.index)

    def undo(self):
        """Восстановить маркер."""
        self.markers_list.insert(self.index, self.marker)


class ModifyMarkerCommand(MarkerCommand):
    """Команда изменения маркера."""
    
    def __init__(self, markers_list: List[Marker], index: int, 
                 old_marker: Marker, new_marker: Marker):
        super().__init__(f"Modify {new_marker.type.name} marker")
        self.markers_list = markers_list
        self.index = index
        self.old_marker = old_marker.copy() if hasattr(old_marker, 'copy') else old_marker
        self.new_marker = new_marker.copy() if hasattr(new_marker, 'copy') else new_marker

    def redo(self):
        """Применить новые значения."""
        if self.index < len(self.markers_list):
            self.markers_list[self.index] = self.new_marker

    def undo(self):
        """Восстановить старые значения."""
        if self.index < len(self.markers_list):
            self.markers_list[self.index] = self.old_marker


class ClearMarkersCommand(MarkerCommand):
    """Команда очистки всех маркеров."""
    
    def __init__(self, markers_list: List[Marker]):
        super().__init__("Clear all markers")
        self.markers_list = markers_list
        self.saved_markers = [
            (m.copy() if hasattr(m, 'copy') else m) for m in markers_list
        ]

    def redo(self):
        """Очистить маркеры."""
        self.markers_list.clear()

    def undo(self):
        """Восстановить маркеры."""
        self.markers_list.clear()
        self.markers_list.extend(self.saved_markers)


class UndoRedoManager(QObject):
    """Менеджер undo/redo операций."""
    
    # Сигналы
    can_undo_changed = Signal(bool)
    can_redo_changed = Signal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.undo_stack = QUndoStack()
        self.undo_stack.canUndoChanged.connect(self._on_can_undo_changed)
        self.undo_stack.canRedoChanged.connect(self._on_can_redo_changed)

    def push_command(self, command: QUndoCommand):
        """Добавить команду в стек."""
        self.undo_stack.push(command)

    def undo(self):
        """Отменить последнюю операцию."""
        self.undo_stack.undo()

    def redo(self):
        """Повторить последнюю отменённую операцию."""
        self.undo_stack.redo()

    def can_undo(self) -> bool:
        """Проверить, можно ли отменить."""
        return self.undo_stack.canUndo()

    def can_redo(self) -> bool:
        """Проверить, можно ли повторить."""
        return self.undo_stack.canRedo()

    def undo_text(self) -> str:
        """Получить текст для кнопки Undo."""
        return self.undo_stack.undoText()

    def redo_text(self) -> str:
        """Получить текст для кнопки Redo."""
        return self.undo_stack.redoText()

    def _on_can_undo_changed(self, can_undo: bool):
        """Сигнал изменения возможности undo."""
        self.can_undo_changed.emit(can_undo)

    def _on_can_redo_changed(self, can_redo: bool):
        """Сигнал изменения возможности redo."""
        self.can_redo_changed.emit(can_redo)

    def clear(self):
        """Очистить стек команд."""
        self.undo_stack.clear()

