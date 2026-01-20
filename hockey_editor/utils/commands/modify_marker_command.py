from typing import List
from .marker_command import MarkerCommand


class ModifyMarkerCommand(MarkerCommand):
    """Команда изменения маркера."""

    def __init__(self, markers_list: List, index: int, old_marker, new_marker):
        super().__init__(markers_list)
        self.index = index
        self.old_marker = old_marker
        self.new_marker = new_marker
        # ИСПРАВЛЕНО: используется event_name вместо type.name
        self.description = f"Modify {old_marker.event_name} marker"

    def execute(self):
        """Выполнить команду (вызывается при первом выполнении)."""
        self.redo()

    def undo(self):
        """Восстановить старый маркер."""
        if 0 <= self.index < len(self.markers):
            self.markers[self.index] = self.old_marker

    def redo(self):
        """Применить новый маркер."""
        if 0 <= self.index < len(self.markers):
            self.markers[self.index] = self.new_marker
