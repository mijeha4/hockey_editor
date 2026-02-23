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

Important:
- This widget works with segments as List[Tuple[int, Marker]] where int is
  the ORIGINAL index in the full markers list (project.markers).
- Original indices are stored in the model via Qt.UserRole.
- Supports ExtendedSelection: Ctrl+Click, Shift+Click for multi-select.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, Signal, QModelIndex
from PySide6.QtGui import QFont, QColor, QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableView, QHeaderView,
    QStyle, QStyledItemDelegate, QStyleOptionViewItem,
    QAbstractItemView, QMenu, QLabel
)

from models.domain.marker import Marker
from models.ui.event_list_model import SegmentTableModel
from services.events.custom_event_manager import get_custom_event_manager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from controllers.filter_controller import FilterController


class SegmentListWidget(QWidget):
    """Widget for displaying segments using virtualized QTableView.

    Supports:
    - Single click: select one row
    - Ctrl+Click: toggle individual row selection
    - Shift+Click: range selection
    - Double click: edit segment
    - Right click: context menu with group operations
    """

    # Emits ORIGINAL marker index (index in project.markers)
    segment_edit_requested = Signal(int)
    segment_delete_requested = Signal(int)
    segment_jump_requested = Signal(int)

    # === НОВЫЕ СИГНАЛЫ для групповых операций ===
    batch_delete_requested = Signal(list)           # List[int] original indices
    batch_change_type_requested = Signal(list, str) # List[int] indices, new_event_name
    batch_export_requested = Signal(list)           # List[int] original indices
    batch_duplicate_requested = Signal(list)        # List[int] original indices

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

        # QTableView
        self.table = QTableView()
        self.table.setModel(self._model)

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
                background-color: #1a4d7a;
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

        # === КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: ExtendedSelection вместо SingleSelection ===
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.verticalHeader().setVisible(False)

        # Мышь для hover
        self.table.setMouseTracking(True)
        self.table.viewport().setMouseTracking(True)

        # Двойной клик → редактирование
        self.table.doubleClicked.connect(self._on_double_clicked)

        # Контекстное меню
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)

        layout.addWidget(self.table)

        # Панель кнопок действий
        self._setup_action_bar(layout)

    def _setup_action_bar(self, parent_layout: QVBoxLayout) -> None:
        """Панель быстрых действий — адаптируется под количество выделенных."""
        action_bar_widget = QWidget()
        action_bar_widget.setFixedHeight(32)
        action_bar_widget.setStyleSheet("background-color: #1e1e1e;")

        action_bar = QHBoxLayout(action_bar_widget)
        action_bar.setContentsMargins(4, 2, 4, 2)
        action_bar.setSpacing(4)

        # Лейбл выделения
        self._selection_label = QLabel("")
        self._selection_label.setStyleSheet(
            "color: #aaaaaa; font-size: 11px; padding: 0 4px;"
        )
        action_bar.addWidget(self._selection_label)

        action_bar.addStretch()

        # Кнопки — текст обновляется динамически
        self._jump_btn = QPushButton("▶ Перейти")
        self._jump_btn.setFixedHeight(24)
        self._jump_btn.setToolTip("Перейти к началу первого выделенного сегмента")
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

        self._change_type_btn = QPushButton("🏷 Тип")
        self._change_type_btn.setFixedHeight(24)
        self._change_type_btn.setToolTip("Изменить тип события для выделенных")
        self._change_type_btn.setStyleSheet(self._get_action_bar_button_style())
        self._change_type_btn.clicked.connect(self._on_change_type_selected)
        self._change_type_btn.setEnabled(False)
        self._change_type_btn.setVisible(False)  # Видна только при множественном выделении
        action_bar.addWidget(self._change_type_btn)

        self._export_btn = QPushButton("📤 Экспорт")
        self._export_btn.setFixedHeight(24)
        self._export_btn.setToolTip("Экспортировать выделенные сегменты")
        self._export_btn.setStyleSheet(self._get_action_bar_button_style())
        self._export_btn.clicked.connect(self._on_export_selected)
        self._export_btn.setEnabled(False)
        self._export_btn.setVisible(False)
        action_bar.addWidget(self._export_btn)

        self._delete_btn = QPushButton("✕ Удалить")
        self._delete_btn.setFixedHeight(24)
        self._delete_btn.setToolTip("Удалить выделенные сегменты")
        self._delete_btn.setStyleSheet(self._get_delete_button_style())
        self._delete_btn.clicked.connect(self._on_delete_selected)
        self._delete_btn.setEnabled(False)
        action_bar.addWidget(self._delete_btn)

        parent_layout.addWidget(action_bar_widget)

    def _setup_selection_handling(self) -> None:
        """Подключить обработчик изменения выделения."""
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API (backward compatible)
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
        return sorted(indices)

    def get_selected_count(self) -> int:
        """Количество выделенных строк."""
        return len(self.table.selectionModel().selectedRows())

    # ──────────────────────────────────────────────────────────────────────────
    # Event handlers — одиночные
    # ──────────────────────────────────────────────────────────────────────────

    def _on_double_clicked(self, index: QModelIndex) -> None:
        """Двойной клик → открыть редактор сегмента."""
        if not index.isValid():
            return
        orig = self._model.get_original_idx_at(index.row())
        if orig is not None:
            self.segment_edit_requested.emit(orig)

    def _on_jump_selected(self) -> None:
        """Кнопка 'Перейти' → перейти к первому выделенному."""
        indices = self.get_selected_original_indices()
        if indices:
            self.segment_jump_requested.emit(indices[0])

    def _on_edit_selected(self) -> None:
        """Кнопка 'Редактировать' → редактировать первый выделенный."""
        indices = self.get_selected_original_indices()
        if indices:
            self.segment_edit_requested.emit(indices[0])

    def _on_delete_selected(self) -> None:
        """Кнопка 'Удалить' → удалить все выделенные."""
        indices = self.get_selected_original_indices()
        if not indices:
            return

        if len(indices) == 1:
            self.segment_delete_requested.emit(indices[0])
        else:
            self.batch_delete_requested.emit(indices)

    def _on_change_type_selected(self) -> None:
        """Кнопка 'Тип' → изменить тип для всех выделенных."""
        indices = self.get_selected_original_indices()
        if not indices:
            return

        new_type = self._show_event_type_picker()
        if new_type:
            self.batch_change_type_requested.emit(indices, new_type)

    def _on_export_selected(self) -> None:
        """Кнопка 'Экспорт' → экспортировать все выделенные."""
        indices = self.get_selected_original_indices()
        if indices:
            self.batch_export_requested.emit(indices)

    # ──────────────────────────────────────────────────────────────────────────
    # Context menu
    # ──────────────────────────────────────────────────────────────────────────

    def _on_context_menu(self, pos) -> None:
        """Контекстное меню — адаптируется к количеству выделенных."""
        indices = self.get_selected_original_indices()
        if not indices:
            return

        count = len(indices)
        menu = QMenu(self)
        menu.setStyleSheet(self._get_context_menu_style())

        if count == 1:
            # Одиночное выделение
            menu.addAction("▶ Перейти к началу", self._on_jump_selected)
            menu.addAction("✎ Редактировать", self._on_edit_selected)
            menu.addSeparator()
            menu.addAction("📋 Дублировать",
                           lambda: self.batch_duplicate_requested.emit(indices))
            menu.addAction("📤 Экспортировать клип",
                           lambda: self.batch_export_requested.emit(indices))
            menu.addSeparator()

            delete_action = menu.addAction(
                "🗑️ Удалить",
                lambda: self.segment_delete_requested.emit(indices[0])
            )
        else:
            # Множественное выделение
            header = menu.addAction(f"📌 Выбрано: {count} сегментов")
            header.setEnabled(False)
            menu.addSeparator()

            menu.addAction(
                f"🏷 Изменить тип ({count})",
                self._on_change_type_selected
            )
            menu.addAction(
                f"📋 Дублировать ({count})",
                lambda: self.batch_duplicate_requested.emit(indices)
            )
            menu.addAction(
                f"📤 Экспортировать ({count})",
                lambda: self.batch_export_requested.emit(indices)
            )
            menu.addSeparator()

            delete_action = menu.addAction(
                f"🗑️ Удалить выделенные ({count})",
                lambda: self.batch_delete_requested.emit(indices)
            )

        menu.exec(self.table.viewport().mapToGlobal(pos))

    # ──────────────────────────────────────────────────────────────────────────
    # Event type picker dialog
    # ──────────────────────────────────────────────────────────────────────────

    def _show_event_type_picker(self) -> Optional[str]:
        """Показать меню выбора типа события. Возвращает event.name или None."""
        events = self.event_manager.get_all_events()
        if not events:
            return None

        menu = QMenu("Выберите тип события", self)
        menu.setStyleSheet(self._get_context_menu_style())

        for event in events:
            color = QColor(event.color) if hasattr(event, 'color') else QColor("#ffffff")
            action = menu.addAction(f"● {event.get_localized_name()}")
            action.setData(event.name)
            # Цветной индикатор через стиль текста
            action.setIcon(self._create_color_icon(color))

        chosen = menu.exec(self._change_type_btn.mapToGlobal(
            self._change_type_btn.rect().bottomLeft()
        ))

        if chosen:
            return chosen.data()
        return None

    def _create_color_icon(self, color: QColor):
        """Создать маленькую иконку-кружок заданного цвета."""
        from PySide6.QtGui import QPixmap, QPainter, QIcon
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(1, 1, 10, 10)
        painter.end()
        return QIcon(pixmap)

    # ──────────────────────────────────────────────────────────────────────────
    # Selection handling
    # ──────────────────────────────────────────────────────────────────────────

    def _on_selection_changed(self, selected, deselected) -> None:
        """Обработка изменения выделения.

        Адаптирует панель кнопок:
        - 0 выделено: всё отключено
        - 1 выделен: Перейти + Редактировать + Удалить
        - 2+ выделено: Тип + Экспорт + Удалить (N), скрыть Перейти/Редактировать
        """
        if self._building_table:
            return

        selected_orig = self.get_selected_original_indices()
        count = len(selected_orig)

        # Обновить лейбл
        if count == 0:
            self._selection_label.setText("")
        elif count == 1:
            self._selection_label.setText("1 сегмент")
        else:
            self._selection_label.setText(f"{count} сегментов")

        # Одиночные кнопки
        self._jump_btn.setEnabled(count >= 1)
        self._jump_btn.setVisible(count <= 1)
        self._edit_btn.setEnabled(count == 1)
        self._edit_btn.setVisible(count <= 1)

        # Групповые кнопки
        self._change_type_btn.setEnabled(count >= 2)
        self._change_type_btn.setVisible(count >= 2)
        self._change_type_btn.setText(f"🏷 Тип ({count})" if count >= 2 else "🏷 Тип")

        self._export_btn.setEnabled(count >= 1)
        self._export_btn.setVisible(count >= 2)
        self._export_btn.setText(f"📤 Экспорт ({count})" if count >= 2 else "📤 Экспорт")

        # Кнопка удаления — всегда видна, текст адаптируется
        self._delete_btn.setEnabled(count >= 1)
        if count >= 2:
            self._delete_btn.setText(f"✕ Удалить ({count})")
        else:
            self._delete_btn.setText("✕ Удалить")

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
    def _get_context_menu_style() -> str:
        return """
            QMenu {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 0px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                margin: 1px 4px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #1a4d7a;
                color: #ffffff;
            }
            QMenu::item:disabled {
                color: #888888;
            }
            QMenu::separator {
                height: 1px;
                background-color: #444444;
                margin: 4px 8px;
            }
        """

    @staticmethod
    def _format_time(seconds: float) -> str:
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"