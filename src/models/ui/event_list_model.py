"""
Event List Model - модели данных для отображения маркеров событий.

Содержит:
- MarkersListModel: одноколоночная модель для QListView (legacy)
- SegmentTableModel: табличная модель для QTableView (новая, виртуализированная)
"""

from typing import List, Tuple, Optional
from PySide6.QtCore import QAbstractListModel, QAbstractTableModel, Qt, QModelIndex, Signal
from PySide6.QtGui import QColor, QFont

from models.domain.marker import Marker
from services.events.custom_event_manager import get_custom_event_manager


# ──────────────────────────────────────────────────────────────────────────────
# Legacy list model (kept for backward compatibility)
# ──────────────────────────────────────────────────────────────────────────────

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
        """Установить предварительно отфильтрованные сегменты."""
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


# ──────────────────────────────────────────────────────────────────────────────
# New table model for virtualized segment list
# ──────────────────────────────────────────────────────────────────────────────

class SegmentTableModel(QAbstractTableModel):
    """Виртуализированная табличная модель для списка сегментов.

    Преимущества над QTableWidget:
    - Данные генерируются по запросу (только видимые строки)
    - Нет создания QTableWidgetItem для каждой ячейки
    - При 1000+ сегментах работает без задержек
    - Поддерживает сортировку через QSortFilterProxyModel

    Колонки:
        0: ID (номер в текущем виде)
        1: Название события (цветное)
        2: Начало (MM:SS)
        3: Конец (MM:SS)
        4: Длительность (MM:SS)

    Роли:
        UserRole: original_idx (int) — оригинальный индекс в project.markers
        UserRole+1: Marker объект
        ForegroundRole: цвет текста для колонки 1
    """

    COLUMNS = ["ID", "Название", "Начало", "Конец", "Длительность"]
    COL_ID = 0
    COL_NAME = 1
    COL_START = 2
    COL_END = 3
    COL_DURATION = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._segments: List[Tuple[int, Marker]] = []
        self._fps: float = 30.0
        self._event_manager = get_custom_event_manager()

        # Кэш шрифтов (создаются один раз)
        self._compact_font = QFont("Segoe UI", 9)
        self._bold_font = QFont("Segoe UI", 9)
        self._bold_font.setBold(True)
        self._mono_font = QFont("Consolas", 9)

    # ──────────────── QAbstractTableModel interface ──────────────────

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._segments)

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()

        if row < 0 or row >= len(self._segments):
            return None

        original_idx, marker = self._segments[row]

        # ─── Display role: текст ячейки ───
        if role == Qt.ItemDataRole.DisplayRole:
            if col == self.COL_ID:
                return str(row + 1)
            elif col == self.COL_NAME:
                event = self._event_manager.get_event(marker.event_name)
                return event.get_localized_name() if event else marker.event_name
            elif col == self.COL_START:
                return self._format_time(marker.start_frame / self._fps)
            elif col == self.COL_END:
                return self._format_time(marker.end_frame / self._fps)
            elif col == self.COL_DURATION:
                duration_frames = max(0, marker.end_frame - marker.start_frame)
                return self._format_time(duration_frames / self._fps)

        # ─── Foreground role: цвет текста ───
        elif role == Qt.ItemDataRole.ForegroundRole:
            if col == self.COL_NAME:
                event = self._event_manager.get_event(marker.event_name)
                if event:
                    return event.get_qcolor()
                return QColor("#ffffff")

        # ─── Font role ───
        elif role == Qt.ItemDataRole.FontRole:
            if col == self.COL_NAME:
                return self._bold_font
            elif col in (self.COL_START, self.COL_END, self.COL_DURATION):
                return self._mono_font
            return self._compact_font

        # ─── Alignment role ───
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if col == self.COL_ID:
                return int(Qt.AlignmentFlag.AlignCenter)
            elif col in (self.COL_START, self.COL_END, self.COL_DURATION):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # ─── Custom roles: original_idx и marker ───
        elif role == Qt.ItemDataRole.UserRole:
            return original_idx
        elif role == Qt.ItemDataRole.UserRole + 1:
            return marker

        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal and 0 <= section < len(self.COLUMNS):
                return self.COLUMNS[section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    # ──────────────── Public API ──────────────────

    def set_segments(self, segments: List[Tuple[int, Marker]]) -> None:
        """Заменить все данные модели.

        Args:
            segments: List of (original_idx, marker) tuples.
        """
        self.beginResetModel()
        self._segments = list(segments)
        self.endResetModel()

    def set_fps(self, fps: float) -> None:
        """Установить FPS для расчёта времени."""
        old_fps = self._fps
        self._fps = fps if fps > 0 else 30.0
        if old_fps != self._fps and self._segments:
            # Обновить колонки времени
            top_left = self.index(0, self.COL_START)
            bottom_right = self.index(len(self._segments) - 1, self.COL_DURATION)
            self.dataChanged.emit(top_left, bottom_right)

    def get_segment_at(self, row: int) -> Tuple[Optional[int], Optional[Marker]]:
        """Получить (original_idx, marker) для строки."""
        if 0 <= row < len(self._segments):
            return self._segments[row]
        return None, None

    def get_original_idx_at(self, row: int) -> Optional[int]:
        """Получить original_idx для строки."""
        if 0 <= row < len(self._segments):
            return self._segments[row][0]
        return None

    def find_row_by_original_idx(self, original_idx: int) -> int:
        """Найти строку по оригинальному индексу. Возвращает -1 если не найден."""
        for row, (orig_idx, _) in enumerate(self._segments):
            if orig_idx == original_idx:
                return row
        return -1

    def get_all_segments(self) -> List[Tuple[int, Marker]]:
        """Получить копию всех сегментов."""
        return list(self._segments)

    @property
    def segment_count(self) -> int:
        """Количество сегментов в модели."""
        return len(self._segments)

    # ──────────────── Helpers ──────────────────

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Форматировать секунды в MM:SS."""
        if seconds < 0:
            seconds = 0
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"