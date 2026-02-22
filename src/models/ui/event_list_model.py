"""
Event List Model - модель данных для QListView с маркерами событий.
"""

from typing import List, Tuple, Optional
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, Signal

from models.domain.marker import Marker


class MarkersListModel(QAbstractListModel):
    """Модель данных для QListView с маркерами событий."""

    marker_play_requested = Signal(int)
    marker_edit_requested = Signal(int)
    marker_delete_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._markers: List[Tuple[int, Marker]] = []
        self._fps: float = 30.0

        self._filter_event_types = set()
        self._filter_has_notes = False
        self._filter_notes_search = ""

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._markers)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._markers):
            return None

        original_idx, marker = self._markers[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return f"#{original_idx + 1}"
        elif role == Qt.ItemDataRole.UserRole:
            return (original_idx, marker)
        elif role == Qt.ItemDataRole.UserRole + 1:
            return self._fps

        return None

    def set_fps(self, fps: float):
        self._fps = fps if fps > 0 else 30.0

    def set_markers(self, all_markers: List[Marker]):
        """Установить полный список маркеров и применить внутренние фильтры."""
        self.beginResetModel()
        self._markers = []
        for idx, marker in enumerate(all_markers):
            if self._passes_filters(marker):
                self._markers.append((idx, marker))
        self.endResetModel()

    def set_filtered_segments(self, segments: List[Tuple[int, Marker]]) -> None:
        """Установить предварительно отфильтрованные сегменты.

        Args:
            segments: List of (original_index, marker) tuples.
        """
        self.beginResetModel()
        self._markers = list(segments)
        self.endResetModel()

    def update_filters(self, event_types: set = None, has_notes: bool = None,
                       notes_search: str = None):
        if event_types is not None:
            self._filter_event_types = event_types
        if has_notes is not None:
            self._filter_has_notes = has_notes
        if notes_search is not None:
            self._filter_notes_search = notes_search.lower().strip()

    def get_marker_at(self, row: int) -> Tuple[Optional[int], Optional[Marker]]:
        if 0 <= row < len(self._markers):
            return self._markers[row]
        return None, None

    def find_row_by_marker_idx(self, marker_idx: int) -> int:
        for row, (orig_idx, _) in enumerate(self._markers):
            if orig_idx == marker_idx:
                return row
        return -1

    def _passes_filters(self, marker: Marker) -> bool:
        if self._filter_event_types and marker.event_name not in self._filter_event_types:
            return False
        if self._filter_has_notes and not (marker.note or "").strip():
            return False
        if self._filter_notes_search and self._filter_notes_search not in (marker.note or "").lower():
            return False
        return True

    def get_filtered_markers(self) -> List[Tuple[int, Marker]]:
        return self._markers.copy()