"""
Event List Model - модель данных для QListView с маркерами событий.
Используется в PreviewWindow для отображения списка событий с фильтрацией.
"""

from typing import List, Tuple, Optional
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex, Signal

from src.models.domain.marker import Marker


class MarkersListModel(QAbstractListModel):
    """
    Модель данных для QListView с маркерами событий.
    Хранит отфильтрованный список маркеров с их оригинальными индексами.
    """

    # Сигналы
    marker_play_requested = Signal(int)  # marker_idx
    marker_edit_requested = Signal(int)  # marker_idx
    marker_delete_requested = Signal(int)  # marker_idx

    def __init__(self, parent=None):
        super().__init__(parent)
        self._markers: List[Tuple[int, Marker]] = []  # [(original_idx, marker), ...]
        self._fps: float = 30.0

        # Фильтры
        self._filter_event_types = set()  # Множество выбранных типов событий
        self._filter_has_notes = False    # Фильтр по наличию заметок
        self._filter_notes_search = ""    # Поиск по тексту заметок

    def rowCount(self, parent=QModelIndex()) -> int:
        """Количество элементов в модели."""
        return len(self._markers)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        """Получить данные для указанного индекса."""
        if not index.isValid() or index.row() >= len(self._markers):
            return None

        original_idx, marker = self._markers[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return f"#{original_idx + 1}"
        elif role == Qt.ItemDataRole.UserRole:
            return (original_idx, marker)
        elif role == Qt.ItemDataRole.UserRole + 1:  # FPS
            return self._fps

        return None

    def set_fps(self, fps: float):
        """Установить FPS для форматирования времени."""
        self._fps = fps

    def set_markers(self, all_markers: List[Marker]):
        """Установить полный список маркеров и применить фильтры."""
        self.beginResetModel()
        self._markers = []

        # Применить фильтры и собрать отфильтрованные маркеры
        for idx, marker in enumerate(all_markers):
            if self._passes_filters(marker):
                self._markers.append((idx, marker))

        self.endResetModel()

    def update_filters(self, event_types: set = None, has_notes: bool = None, notes_search: str = None):
        """Обновить фильтры и пересчитать список."""
        if event_types is not None:
            self._filter_event_types = event_types
        if has_notes is not None:
            self._filter_has_notes = has_notes
        if notes_search is not None:
            self._filter_notes_search = notes_search.lower().strip()

        # Пересчитать список с новыми фильтрами
        # (предполагается, что у нас есть доступ к полному списку маркеров)
        # В PreviewWindow мы вызовем set_markers() заново

    def get_marker_at(self, row: int) -> Optional[Tuple[int, Marker]]:
        """Получить маркер по индексу строки."""
        if 0 <= row < len(self._markers):
            return self._markers[row]
        return None

    def find_row_by_marker_idx(self, marker_idx: int) -> int:
        """Найти строку по оригинальному индексу маркера."""
        for row, (orig_idx, marker) in enumerate(self._markers):
            if orig_idx == marker_idx:
                return row
        return -1

    def _passes_filters(self, marker: Marker) -> bool:
        """Проверить, проходит ли маркер через текущие фильтры."""
        # Фильтр по типу события
        if self._filter_event_types and marker.event_name not in self._filter_event_types:
            return False

        # Фильтр по заметкам
        if self._filter_has_notes and not marker.note.strip():
            return False

        # Фильтр по поиску в заметках
        if self._filter_notes_search and self._filter_notes_search not in marker.note.lower():
            return False

        return True

    def get_filtered_markers(self) -> List[Tuple[int, Marker]]:
        """Получить текущий отфильтрованный список маркеров."""
        return self._markers.copy()
