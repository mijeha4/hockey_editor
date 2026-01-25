"""
Segment List Widget - displays video segments in a data grid format.

Data Grid with columns:
- ID: Segment number
- Название: Event name (colored)
- Начало: Start time (monospace, right-aligned)
- Конец: End time (monospace, right-aligned)
- Длительность: Duration (monospace, right-aligned)
- Действия: Action buttons (edit, delete, jump)
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QHBoxLayout, QStyle
)
from ..models.marker import Marker
from ..utils.custom_events import get_custom_event_manager


class SegmentListWidget(QWidget):
    """Widget for displaying segments in a data grid."""

    # Signals
    segment_edit_requested = Signal(int)  # marker_idx
    segment_delete_requested = Signal(int)  # marker_idx
    segment_jump_requested = Signal(int)  # marker_idx

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fps = 30.0  # default, will be updated
        self.segments = []  # list of (marker_idx, marker) tuples
        self.event_manager = get_custom_event_manager()

        self.setup_ui()

    def setup_ui(self):
        """Create the main UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create table widget
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Начало", "Конец", "Длительность", ""])

        # Configure table appearance
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #444444;
                gridline-color: #444444;
                selection-background-color: #444444;
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

        # Configure headers
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Название
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Начало
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Конец
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Длительность
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Действия

        # Set column widths
        self.table.setColumnWidth(0, 30)   # ID
        self.table.setColumnWidth(2, 60)   # Начало
        self.table.setColumnWidth(3, 60)   # Конец
        self.table.setColumnWidth(4, 70)   # Длительность
        self.table.setColumnWidth(5, 90)   # Действия

        # Configure table behavior
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Set row height to 25 pixels (half of original 50)
        self.table.verticalHeader().setDefaultSectionSize(25)
        self.table.verticalHeader().setVisible(False)

        # Connect signals
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu_requested)

        layout.addWidget(self.table)

    def set_fps(self, fps: float):
        """Update FPS for time formatting."""
        self.fps = fps
        self.refresh_segments()

    def set_segments(self, segments: list):
        """Set the list of segments to display.

        Args:
            segments: List of (marker_idx, marker) tuples
        """
        self.segments = segments
        self.refresh_segments()

    def refresh_segments(self):
        """Refresh all table rows."""
        self.table.setRowCount(0)  # Clear table

        for marker_idx, marker in self.segments:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Column 0: ID
            id_item = QTableWidgetItem(str(marker_idx + 1))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setFont(self._get_compact_font())
            self.table.setItem(row, 0, id_item)

            # Column 1: Название (Event name)
            event = self.event_manager.get_event(marker.event_name)
            event_name = event.get_localized_name() if event else marker.event_name
            event_color = event.get_qcolor().name() if event else "#ffffff"

            name_item = QTableWidgetItem(event_name)
            name_item.setForeground(QColor(event_color))
            name_item.setFont(self._get_compact_font())
            name_item.setFont(self._get_bold_font())
            self.table.setItem(row, 1, name_item)

            # Column 2: Начало (Start time)
            start_time = self._format_time(marker.start_frame / self.fps)
            start_item = QTableWidgetItem(start_time)
            start_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            start_item.setFont(self._get_monospace_font())
            self.table.setItem(row, 2, start_item)

            # Column 3: Конец (End time)
            end_time = self._format_time(marker.end_frame / self.fps)
            end_item = QTableWidgetItem(end_time)
            end_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            end_item.setFont(self._get_monospace_font())
            self.table.setItem(row, 3, end_item)

            # Column 4: Длительность (Duration)
            duration_frames = marker.end_frame - marker.start_frame
            duration_time = self._format_time(duration_frames / self.fps)
            duration_item = QTableWidgetItem(duration_time)
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            duration_item.setFont(self._get_monospace_font())
            self.table.setItem(row, 4, duration_item)

            # Column 5: Действия (Action buttons)
            actions_widget = self._create_actions_widget(marker_idx)
            self.table.setCellWidget(row, 5, actions_widget)

            # Store marker_idx in the row for context menu
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, marker_idx)

    def _create_actions_widget(self, marker_idx: int) -> QWidget:
        """Create action buttons widget for a row."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Jump button
        jump_btn = QPushButton()
        jump_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        jump_btn.setFixedSize(20, 20)
        jump_btn.setToolTip("Перейти к началу сегмента")
        jump_btn.setStyleSheet(self._get_action_button_style())
        jump_btn.clicked.connect(lambda: self.segment_jump_requested.emit(marker_idx))
        layout.addWidget(jump_btn)

        # Edit button
        edit_btn = QPushButton()
        edit_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        edit_btn.setFixedSize(20, 20)
        edit_btn.setToolTip("Редактировать сегмент")
        edit_btn.setStyleSheet(self._get_action_button_style())
        edit_btn.clicked.connect(lambda: self.segment_edit_requested.emit(marker_idx))
        layout.addWidget(edit_btn)

        # Delete button
        delete_btn = QPushButton()
        delete_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        delete_btn.setFixedSize(20, 20)
        delete_btn.setToolTip("Удалить сегмент")
        delete_btn.setStyleSheet(self._get_action_button_style())
        delete_btn.clicked.connect(lambda: self.segment_delete_requested.emit(marker_idx))
        layout.addWidget(delete_btn)

        layout.addStretch()
        return widget

    def _get_compact_font(self) -> QFont:
        """Get compact font for table cells."""
        font = QFont()
        font.setPointSize(9)
        font.setFamily("Segoe UI")
        return font

    def _get_bold_font(self) -> QFont:
        """Get bold font for event names."""
        font = self._get_compact_font()
        font.setBold(True)
        return font

    def _get_monospace_font(self) -> QFont:
        """Get monospace font for time codes."""
        font = QFont()
        font.setPointSize(9)
        font.setFamily("Consolas, 'Courier New', monospace")
        return font

    def _get_action_button_style(self) -> str:
        """Get consistent style for action buttons."""
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

    def _format_time(self, seconds: float) -> str:
        """Format time as MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    def _on_item_double_clicked(self, item):
        """Handle double-click on table item."""
        if item:
            marker_idx = item.data(Qt.ItemDataRole.UserRole)
            if marker_idx is not None:
                self.segment_edit_requested.emit(marker_idx)

    def _on_context_menu_requested(self, pos):
        """Handle right-click context menu."""
        item = self.table.itemAt(pos)
        if item:
            marker_idx = item.data(Qt.ItemDataRole.UserRole)
            if marker_idx is not None:
                # Could implement context menu here if needed
                pass

    def clear_segments(self):
        """Clear all segments."""
        self.segments = []
        self.table.setRowCount(0)
