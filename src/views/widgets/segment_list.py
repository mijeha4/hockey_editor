"""
Segment List Widget - displays video segments in a data grid format.

Table columns:
- ID: Row number in the current (filtered) view
- Название: Event name (colored)
- Начало: Start time
- Конец: End time
- Длительность: Duration
- Действия: Action buttons (jump/edit/delete)

Important:
- This widget works with segments as List[Tuple[int, Marker]] where int is
  the ORIGINAL index in the full markers list (project.markers).
- We store original_idx in Qt.UserRole so actions always refer to correct marker
  even after filtering.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QStyle
)

from models.domain.marker import Marker
from services.events.custom_event_manager import get_custom_event_manager

# Optional typing only
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from controllers.filter_controller import FilterController


class SegmentListWidget(QWidget):
    """Widget for displaying segments in a data grid."""

    # Emits ORIGINAL marker index (index in project.markers)
    segment_edit_requested = Signal(int)
    segment_delete_requested = Signal(int)
    segment_jump_requested = Signal(int)

    # Optional: notify selection change using original indices
    selection_changed = Signal(list)  # List[int] of original indices

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.fps: float = 30.0
        self.segments: List[Tuple[int, Marker]] = []  # (original_idx, marker)

        self.event_manager = get_custom_event_manager()
        self.filter_controller: Optional["FilterController"] = None

        self._building_table: bool = False  # guard to avoid selection recursion

        self._setup_ui()
        self._setup_selection_handling()

    # ──────────────────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Начало", "Конец", "Длительность", ""])

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444444;
                gridline-color: #444444;
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
                font-size: 11px;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #333333;
                border: 1px solid #555555;
            }
        """)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 30)
        self.table.setColumnWidth(2, 60)
        self.table.setColumnWidth(3, 60)
        self.table.setColumnWidth(4, 70)
        self.table.setColumnWidth(5, 90)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setDefaultSectionSize(25)
        self.table.verticalHeader().setVisible(False)

        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.table.itemClicked.connect(self._on_item_clicked)

        layout.addWidget(self.table)

    def _setup_selection_handling(self) -> None:
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def set_filter_controller(self, filter_controller: Optional["FilterController"]) -> None:
        """Bind FilterController to sync external filter changes."""
        # disconnect old
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
        self.segments = list(segments)
        self._rebuild_table()

    def set_markers(self, markers: List[Marker]) -> None:
        """Compatibility method: set unindexed markers (original indices assumed)."""
        self.set_segments([(i, m) for i, m in enumerate(markers)])

    def set_fps(self, fps: float) -> None:
        self.fps = fps if fps > 0 else 30.0
        self._rebuild_table()

    def clear_segments(self) -> None:
        self.segments.clear()
        self.table.setRowCount(0)

    def get_selected_original_indices(self) -> List[int]:
        indices: List[int] = []
        for index in self.table.selectionModel().selectedRows():
            row = index.row()
            orig = self._original_idx_from_row(row)
            if orig is not None:
                indices.append(orig)
        return indices

    # ──────────────────────────────────────────────────────────────────────────
    # Rendering
    # ──────────────────────────────────────────────────────────────────────────

    def _rebuild_table(self) -> None:
        self._building_table = True
        try:
            self.table.blockSignals(True)
            self.table.setRowCount(0)

            for view_row, (original_idx, marker) in enumerate(self.segments):
                self.table.insertRow(view_row)

                # Column 0: ID in the current view (1..N)
                id_item = QTableWidgetItem(str(view_row + 1))
                id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                id_item.setFont(self._get_compact_font())
                id_item.setData(Qt.ItemDataRole.UserRole, original_idx)
                self.table.setItem(view_row, 0, id_item)

                # Column 1: Event name (localized, colored)
                event = self.event_manager.get_event(marker.event_name)
                event_name = event.get_localized_name() if event else marker.event_name
                event_color = event.get_qcolor().name() if event else "#ffffff"

                name_item = QTableWidgetItem(event_name)
                name_item.setForeground(QColor(event_color))
                name_item.setFont(self._get_bold_font())
                self.table.setItem(view_row, 1, name_item)

                # Column 2: Start time
                start_item = QTableWidgetItem(self._format_time(marker.start_frame / self.fps))
                start_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                start_item.setFont(self._get_monospace_font())
                self.table.setItem(view_row, 2, start_item)

                # Column 3: End time
                end_item = QTableWidgetItem(self._format_time(marker.end_frame / self.fps))
                end_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                end_item.setFont(self._get_monospace_font())
                self.table.setItem(view_row, 3, end_item)

                # Column 4: Duration
                duration_frames = max(0, marker.end_frame - marker.start_frame)
                dur_item = QTableWidgetItem(self._format_time(duration_frames / self.fps))
                dur_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                dur_item.setFont(self._get_monospace_font())
                self.table.setItem(view_row, 4, dur_item)

                # Column 5: Actions
                actions_widget = self._create_actions_widget(original_idx)
                self.table.setCellWidget(view_row, 5, actions_widget)

        finally:
            self.table.blockSignals(False)
            self._building_table = False

    # ──────────────────────────────────────────────────────────────────────────
    # Actions / row helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _original_idx_from_row(self, row: int) -> Optional[int]:
        item = self.table.item(row, 0)
        if not item:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return int(data) if data is not None else None

    def _create_actions_widget(self, original_idx: int) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        jump_btn = QPushButton()
        jump_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        jump_btn.setFixedSize(20, 20)
        jump_btn.setToolTip("Перейти к началу сегмента")
        jump_btn.setStyleSheet(self._get_action_button_style())
        jump_btn.setProperty("original_idx", original_idx)
        jump_btn.clicked.connect(self._on_jump_button_clicked)
        layout.addWidget(jump_btn)

        edit_btn = QPushButton()
        edit_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        edit_btn.setFixedSize(20, 20)
        edit_btn.setToolTip("Редактировать сегмент")
        edit_btn.setStyleSheet(self._get_action_button_style())
        edit_btn.setProperty("original_idx", original_idx)
        edit_btn.clicked.connect(self._on_edit_button_clicked)
        layout.addWidget(edit_btn)

        delete_btn = QPushButton()
        delete_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        delete_btn.setFixedSize(20, 20)
        delete_btn.setToolTip("Удалить сегмент")
        delete_btn.setStyleSheet(self._get_action_button_style())
        delete_btn.setProperty("original_idx", original_idx)
        delete_btn.clicked.connect(self._on_delete_button_clicked)
        layout.addWidget(delete_btn)

        layout.addStretch()
        return widget

    def _on_item_clicked(self, item: QTableWidgetItem) -> None:
        if item:
            self.table.selectRow(item.row())

    def _on_item_double_clicked(self, item: QTableWidgetItem) -> None:
        if not item:
            return
        orig = self._original_idx_from_row(item.row())
        if orig is not None:
            self.segment_edit_requested.emit(orig)

    def _on_jump_button_clicked(self) -> None:
        btn = self.sender()
        if not btn:
            return
        orig = btn.property("original_idx")
        if orig is not None:
            self.segment_jump_requested.emit(int(orig))

    def _on_edit_button_clicked(self) -> None:
        btn = self.sender()
        if not btn:
            return
        orig = btn.property("original_idx")
        if orig is not None:
            self.segment_edit_requested.emit(int(orig))

    def _on_delete_button_clicked(self) -> None:
        btn = self.sender()
        if not btn:
            return
        orig = btn.property("original_idx")
        if orig is not None:
            self.segment_delete_requested.emit(int(orig))

    # ──────────────────────────────────────────────────────────────────────────
    # Selection handling (NO feedback into FilterController!)
    # ──────────────────────────────────────────────────────────────────────────

    def _on_selection_changed(self, selected, deselected) -> None:
        """Handle table selection change.

        IMPORTANT: We only emit selection_changed signal for other components
        (e.g. timeline highlighting). We do NOT push selection back into
        FilterController — that would create a feedback loop where selecting
        a row filters out all other rows.
        """
        if self._building_table:
            return

        selected_orig = self.get_selected_original_indices()
        self.selection_changed.emit(selected_orig)

    def _on_external_filters_changed(self) -> None:
        """When external filters change, table data will usually be reset
        by the main controller. We clear selection to avoid stale state."""
        if not self._building_table:
            self.table.clearSelection()

    # ──────────────────────────────────────────────────────────────────────────
    # Fonts / formatting
    # ──────────────────────────────────────────────────────────────────────────

    def _get_compact_font(self) -> QFont:
        font = QFont()
        font.setPointSize(9)
        font.setFamily("Segoe UI")
        return font

    def _get_bold_font(self) -> QFont:
        font = self._get_compact_font()
        font.setBold(True)
        return font

    def _get_monospace_font(self) -> QFont:
        font = QFont()
        font.setPointSize(9)
        font.setFamily("Consolas, 'Courier New', monospace")
        return font

    def _get_action_button_style(self) -> str:
        return """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #cccccc;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #444444;
                border-radius: 3px;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #555555;
            }
        """

    @staticmethod
    def _format_time(seconds: float) -> str:
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"