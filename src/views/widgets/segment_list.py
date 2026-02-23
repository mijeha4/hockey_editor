"""
Segment List Widget - displays video segments using a virtualized table.

Uses QTableView + SegmentTableModel instead of QTableWidget for performance.
At 500+ segments, QTableWidget creates thousands of widget objects and slows down.
QTableView only renders visible rows, keeping the UI responsive.

Table columns:
- ID: Row number in the current (filtered) view
- Название: Event name (colored)
- Начало: Start time
- Конец: End time
- Длительность: Duration
- Действия: Action buttons (jump/edit/delete) via delegate

Important:
- This widget works with segments as List[Tuple[int, Marker]] where int is
  the ORIGINAL index in the full markers list (project.markers).
- Original indices are stored in the model via Qt.UserRole.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, Signal, QModelIndex
from PySide6.QtGui import QFont, QColor, QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableView, QHeaderView,
    QStyle, QStyledItemDelegate, QStyleOptionViewItem,
    QAbstractItemView
)

from models.domain.marker import Marker
from models.ui.event_list_model import SegmentTableModel
from services.events.custom_event_manager import get_custom_event_manager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from controllers.filter_controller import FilterController


class ActionButtonDelegate(QStyledItemDelegate):
    """Делегат для отрисовки кнопок действий в последней колонке.

    Рисует три кнопки: Перейти (▶), Редактировать (✎), Удалить (✕).
    Обрабатывает клики по областям кнопок.
    """

    # Размеры кнопок
    BUTTON_SIZE = 20
    BUTTON_SPACING = 4
    BUTTON_MARGIN = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered_row: int = -1
        self._hovered_btn: int = -1  # 0=jump, 1=edit, 2=delete

    def paint(self, painter, option: QStyleOptionViewItem, index: QModelIndex):
        """Отрисовка трёх кнопок-иконок."""
        painter.save()

        # Фон ячейки
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#444444"))
        else:
            painter.fillRect(option.rect, QColor("#2a2a2a"))

        # Позиции кнопок
        buttons = self._get_button_rects(option.rect)
        icons = ["▶", "✎", "✕"]
        colors = ["#88cc88", "#88aaff", "#ff8888"]
        tooltips_idx = [0, 1, 2]

        row = index.row()

        for i, (btn_rect, icon, color) in enumerate(zip(buttons, icons, colors)):
            # Подсветка при hover
            is_hovered = (row == self._hovered_row and i == self._hovered_btn)

            if is_hovered:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor("#555555"))
                painter.drawRoundedRect(btn_rect, 3, 3)

            painter.setPen(QColor(color))
            font = QFont("Segoe UI", 10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, icon)

        painter.restore()

    def sizeHint(self, option, index):
        """Минимальный размер для трёх кнопок."""
        from PySide6.QtCore import QSize
        total_width = (
            self.BUTTON_MARGIN * 2
            + self.BUTTON_SIZE * 3
            + self.BUTTON_SPACING * 2
        )
        return QSize(total_width, self.BUTTON_SIZE + 4)

    def editorEvent(self, event, model, option, index):
        """Обработка кликов по кнопкам."""
        if not isinstance(event, QMouseEvent):
            return False

        if event.type() not in (
            QMouseEvent.Type.MouseButtonRelease,
            QMouseEvent.Type.MouseButtonPress,
        ):
            return False

        if event.type() == QMouseEvent.Type.MouseButtonPress:
            return False  # Ждём release

        buttons = self._get_button_rects(option.rect)
        click_pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()

        original_idx = model.data(index, Qt.ItemDataRole.UserRole)
        if original_idx is None:
            # Пробуем через модель напрямую (если используется proxy)
            source_model = model
            source_index = index
            if hasattr(model, 'sourceModel'):
                source_model = model.sourceModel()
                source_index = model.mapToSource(index)
            original_idx = source_model.get_original_idx_at(source_index.row())

        if original_idx is None:
            return False

        parent_widget = self.parent()

        for i, btn_rect in enumerate(buttons):
            if btn_rect.contains(click_pos):
                if i == 0 and parent_widget:  # Jump
                    parent_widget.segment_jump_requested.emit(int(original_idx))
                elif i == 1 and parent_widget:  # Edit
                    parent_widget.segment_edit_requested.emit(int(original_idx))
                elif i == 2 and parent_widget:  # Delete
                    parent_widget.segment_delete_requested.emit(int(original_idx))
                return True

        return False

    def _get_button_rects(self, cell_rect):
        """Вычислить прямоугольники для трёх кнопок."""
        from PySide6.QtCore import QRect

        x_start = cell_rect.left() + self.BUTTON_MARGIN
        y_center = cell_rect.center().y()
        y_top = y_center - self.BUTTON_SIZE // 2

        rects = []
        for i in range(3):
            x = x_start + i * (self.BUTTON_SIZE + self.BUTTON_SPACING)
            rects.append(QRect(x, y_top, self.BUTTON_SIZE, self.BUTTON_SIZE))
        return rects

    def set_hovered(self, row: int, btn_idx: int):
        """Установить hover состояние для кнопки."""
        self._hovered_row = row
        self._hovered_btn = btn_idx


class SegmentListWidget(QWidget):
    """Widget for displaying segments using virtualized QTableView.

    Migration from QTableWidget to QTableView + SegmentTableModel:
    - Данные не дублируются в виджетах — генерируются по запросу
    - При 1000+ сегментов UI не тормозит
    - Все публичные API сохранены для обратной совместимости
    """

    # Emits ORIGINAL marker index (index in project.markers)
    segment_edit_requested = Signal(int)
    segment_delete_requested = Signal(int)
    segment_jump_requested = Signal(int)

    # Notify selection change using original indices
    selection_changed = Signal(list)  # List[int] of original indices

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.fps: float = 30.0
        self.segments: List[Tuple[int, Marker]] = []  # kept for compat

        self.event_manager = get_custom_event_manager()
        self.filter_controller: Optional["FilterController"] = None

        self._building_table: bool = False

        # Модель данных
        self._model = SegmentTableModel(self)

        self._setup_ui()
        self._setup_selection_handling()

    # ──────────────────────────────────────────────────────────────────────────
    # UI Setup
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # QTableView вместо QTableWidget
        self.table = QTableView()
        self.table.setModel(self._model)

        # Делегат для колонки действий
        self._action_delegate = ActionButtonDelegate(self)
        # Колонка действий будет виртуальной 5-й (добавим в модель как пустую)
        # Вместо этого используем делегат на последней реальной колонке

        self.table.setStyleSheet("""
            QTableView {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444444;
                gridline-color: #444444;
            }
            QTableView::item {
                padding: 2px;
                border-bottom: 1px solid #333333;
            }
            QTableView::item:selected {
                background-color: #444444;
            }
            QHeaderView::section {
                background-color: #333333;
                color: #ffffff;
                padding: 4px;
                border: 1px solid #555555;
                font-weight: bold;
                font-size: 11px;
            }
            QTableView QTableCornerButton::section {
                background-color: #333333;
                border: 1px solid #555555;
            }
        """)

        # Настройка заголовков
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 30)
        self.table.setColumnWidth(2, 60)
        self.table.setColumnWidth(3, 60)
        self.table.setColumnWidth(4, 70)

        # Настройки поведения
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.verticalHeader().setVisible(False)

        # Включить отслеживание мыши для hover эффектов
        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)

        # Двойной клик → редактирование
        self.table.doubleClicked.connect(self._on_double_clicked)

        layout.addWidget(self.table)

        # Панель кнопок действий под таблицей
        self._setup_action_bar(layout)

    def _setup_action_bar(self, parent_layout: QVBoxLayout) -> None:
        """Панель быстрых действий для выделенного сегмента."""
        action_bar = QHBoxLayout()
        action_bar.setContentsMargins(2, 2, 2, 2)
        action_bar.setSpacing(4)

        self._jump_btn = QPushButton("▶ Перейти")
        self._jump_btn.setFixedHeight(24)
        self._jump_btn.setToolTip("Перейти к началу выделенного сегмента")
        self._jump_btn.setStyleSheet(self._get_action_bar_button_style())
        self._jump_btn.clicked.connect(self._on_jump_selected)
        self._jump_btn.setEnabled(False)
        action_bar.addWidget(self._jump_btn)

        self._edit_btn = QPushButton("✎ Редактировать")
        self._edit_btn.setFixedHeight(24)
        self._edit_btn.setToolTip("Редактировать выделенный сегмент")
        self._edit_btn.setStyleSheet(self._get_action_bar_button_style())
        self._edit_btn.clicked.connect(self._on_edit_selected)
        self._edit_btn.setEnabled(False)
        action_bar.addWidget(self._edit_btn)

        self._delete_btn = QPushButton("✕ Удалить")
        self._delete_btn.setFixedHeight(24)
        self._delete_btn.setToolTip("Удалить выделенный сегмент")
        self._delete_btn.setStyleSheet(self._get_delete_button_style())
        self._delete_btn.clicked.connect(self._on_delete_selected)
        self._delete_btn.setEnabled(False)
        action_bar.addWidget(self._delete_btn)

        action_bar.addStretch()
        parent_layout.addLayout(action_bar)

    def _setup_selection_handling(self) -> None:
        """Подключить обработчик изменения выделения."""
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API (backward compatible with old QTableWidget version)
    # ──────────────────────────────────────────────────────────────────────────

    def set_filter_controller(self, filter_controller: Optional["FilterController"]) -> None:
        """Bind FilterController to sync external filter changes."""
        if self.filter_controller is not None:
            try:
                self.filter_controller.filters_changed.disconnect(self._on_external_filters_changed)
            except Exception:
                pass

        self.filter_controller = filter_controller

        if self.filter_controller is not None:
            self.filter_controller.filters_changed.connect(self._on_external_filters_changed)

    def set_segments(self, segments: List[Tuple[int, Marker]]) -> None:
        """Set segments as list of (original_idx, marker)."""
        self._building_table = True
        try:
            self.segments = list(segments)
            self._model.set_segments(segments)
        finally:
            self._building_table = False

    def set_markers(self, markers: List[Marker]) -> None:
        """Compatibility method: set unindexed markers."""
        self.set_segments([(i, m) for i, m in enumerate(markers)])

    def set_fps(self, fps: float) -> None:
        self.fps = fps if fps > 0 else 30.0
        self._model.set_fps(self.fps)

    def clear_segments(self) -> None:
        self.segments.clear()
        self._model.set_segments([])

    def get_selected_original_indices(self) -> List[int]:
        """Получить оригинальные индексы выделенных строк."""
        indices: List[int] = []
        for index in self.table.selectionModel().selectedRows():
            row = index.row()
            orig = self._model.get_original_idx_at(row)
            if orig is not None:
                indices.append(orig)
        return indices

    # ──────────────────────────────────────────────────────────────────────────
    # Event handlers
    # ──────────────────────────────────────────────────────────────────────────

    def _on_double_clicked(self, index: QModelIndex) -> None:
        """Двойной клик → открыть редактор сегмента."""
        if not index.isValid():
            return
        orig = self._model.get_original_idx_at(index.row())
        if orig is not None:
            self.segment_edit_requested.emit(orig)

    def _on_jump_selected(self) -> None:
        """Кнопка 'Перейти' → перейти к выделенному."""
        indices = self.get_selected_original_indices()
        if indices:
            self.segment_jump_requested.emit(indices[0])

    def _on_edit_selected(self) -> None:
        """Кнопка 'Редактировать' → редактировать выделенный."""
        indices = self.get_selected_original_indices()
        if indices:
            self.segment_edit_requested.emit(indices[0])

    def _on_delete_selected(self) -> None:
        """Кнопка 'Удалить' → удалить выделенный."""
        indices = self.get_selected_original_indices()
        if indices:
            self.segment_delete_requested.emit(indices[0])

    # ──────────────────────────────────────────────────────────────────────────
    # Selection handling
    # ──────────────────────────────────────────────────────────────────────────

    def _on_selection_changed(self, selected, deselected) -> None:
        """Обработка изменения выделения.

        НЕ пушит выделение в FilterController — это вызвало бы
        feedback loop, где клик по строке отфильтровывает остальные.
        """
        if self._building_table:
            return

        selected_orig = self.get_selected_original_indices()
        has_selection = len(selected_orig) > 0

        # Обновить состояние кнопок
        self._jump_btn.setEnabled(has_selection)
        self._edit_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)

        self.selection_changed.emit(selected_orig)

    def _on_external_filters_changed(self) -> None:
        """При изменении внешних фильтров — сбросить выделение."""
        if not self._building_table:
            self.table.clearSelection()

    # ──────────────────────────────────────────────────────────────────────────
    # Styles
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _get_action_bar_button_style() -> str:
        return """
            QPushButton {
                background-color: #333333;
                color: #cccccc;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #444444;
                color: #ffffff;
                border-color: #666666;
            }
            QPushButton:pressed {
                background-color: #555555;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
                border-color: #444444;
            }
        """

    @staticmethod
    def _get_delete_button_style() -> str:
        return """
            QPushButton {
                background-color: #333333;
                color: #ff8888;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5a2020;
                color: #ff4444;
                border-color: #883333;
            }
            QPushButton:pressed {
                background-color: #6a3030;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #664444;
                border-color: #444444;
            }
        """

    @staticmethod
    def _format_time(seconds: float) -> str:
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"