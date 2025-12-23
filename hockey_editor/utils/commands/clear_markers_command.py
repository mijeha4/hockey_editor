from typing import List
from .marker_command import MarkerCommand


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
