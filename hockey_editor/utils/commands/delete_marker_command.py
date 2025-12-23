from typing import List
from .marker_command import MarkerCommand


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
