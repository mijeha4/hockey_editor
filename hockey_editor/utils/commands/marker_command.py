from typing import List
from .undo_command import QUndoCommand


class MarkerCommand(QUndoCommand):
    """Базовый класс для команд операций с маркерами."""

    def __init__(self, markers_list: List):
        super().__init__()
        self.markers = markers_list
