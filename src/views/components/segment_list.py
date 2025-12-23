from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from typing import List, Dict


class SegmentList(QWidget):
    """Виджет для отображения списка сегментов в табличном виде."""

    # Сигналы
    selection_changed = Signal(int)  # segment_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fps = 30.0
        self._setup_ui()

    def _setup_ui(self):
        """Создать интерфейс."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Создать таблицу
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Тип события", "Начало", "Конец", "Длительность"])

        # Стилизация под темную тему
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444444;
                gridline-color: #444444;
                selection-background-color: #444444;
                alternate-background-color: #333333;
            }
            QTableWidget::item {
                padding: 2px;
                border-bottom: 1px solid #333333;
            }
            QTableWidget::item:selected {
                background-color: #444444;
            }
            QHeaderView::section {
                background-color: #333333;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #555555;
                font-weight: bold;
                font-size: 10px;
            }
        """)

        # Настройка заголовков
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Тип события
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Начало
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Конец
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Длительность

        # Ширина колонок
        self.table.setColumnWidth(0, 30)   # ID
        self.table.setColumnWidth(2, 60)   # Начало
        self.table.setColumnWidth(3, 60)   # Конец
        self.table.setColumnWidth(4, 70)   # Длительность

        # Настройки поведения таблицы
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Высота строк
        self.table.verticalHeader().setDefaultSectionSize(25)
        self.table.verticalHeader().setVisible(False)

        # Подключить сигналы
        self.table.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(self.table)

    def set_segments(self, segments_data: List[Dict]):
        """
        Установить сегменты для отображения.
        segments_data: [{'id': int, 'event_name': str, 'start_frame': int,
                        'end_frame': int, 'color': str}, ...]
        """
        self.table.setRowCount(0)  # Очистить таблицу

        for segment in segments_data:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # ID
            id_item = QTableWidgetItem(str(segment['id'] + 1))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setFont(self._get_compact_font())
            self.table.setItem(row, 0, id_item)

            # Тип события
            event_name = segment['event_name']
            event_item = QTableWidgetItem(event_name)
            event_item.setForeground(QColor(segment.get('color', '#ffffff')))
            event_item.setFont(self._get_bold_font())
            self.table.setItem(row, 1, event_item)

            # Начало
            start_time = self._format_time(segment['start_frame'] / self.fps)
            start_item = QTableWidgetItem(start_time)
            start_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            start_item.setFont(self._get_monospace_font())
            self.table.setItem(row, 2, start_item)

            # Конец
            end_time = self._format_time(segment['end_frame'] / self.fps)
            end_item = QTableWidgetItem(end_time)
            end_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            end_item.setFont(self._get_monospace_font())
            self.table.setItem(row, 3, end_item)

            # Длительность
            duration_frames = segment['end_frame'] - segment['start_frame']
            duration_time = self._format_time(duration_frames / self.fps)
            duration_item = QTableWidgetItem(duration_time)
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            duration_item.setFont(self._get_monospace_font())
            self.table.setItem(row, 4, duration_item)

    def set_fps(self, fps: float):
        """Установить FPS для форматирования времени."""
        self.fps = fps

    def _on_selection_changed(self):
        """Обработка изменения выделения."""
        selected_items = self.table.selectedItems()
        if selected_items:
            # Получить ID сегмента из первой колонки
            row = selected_items[0].row()
            id_item = self.table.item(row, 0)
            if id_item:
                segment_id = int(id_item.text()) - 1  # -1 потому что отображаем с 1
                self.selection_changed.emit(segment_id)

    def _get_compact_font(self) -> QFont:
        """Получить компактный шрифт."""
        font = QFont()
        font.setPointSize(9)
        font.setFamily("Segoe UI")
        return font

    def _get_bold_font(self) -> QFont:
        """Получить жирный шрифт."""
        font = self._get_compact_font()
        font.setBold(True)
        return font

    def _get_monospace_font(self) -> QFont:
        """Получить моноширинный шрифт."""
        font = QFont()
        font.setPointSize(9)
        font.setFamily("Consolas, 'Courier New', monospace")
        return font

    def _format_time(self, seconds: float) -> str:
        """Форматировать время как MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"
