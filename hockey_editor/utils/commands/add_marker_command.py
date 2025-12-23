from typing import List
from .marker_command import MarkerCommand


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
