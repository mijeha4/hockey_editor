"""
Segment List Widget - Displays video segments in a table format.

Shows segments with filtering and action controls.
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PySide6.QtCore import Qt

# Импорты для работы из корня проекта (main.py добавляет src в sys.path)
from models.domain.marker import Marker


class SegmentListWidget(QWidget):
    """Widget for displaying and managing video segments in a table."""

    def __init__(self, parent: Optional[QWidget] = None, filter_controller=None) -> None:
        super().__init__(parent)
        self.segments: List[Marker] = []
        self.fps: float = 30.0  # Default FPS
        self.filter_controller = filter_controller
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Create the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Top control panel
        self._create_control_panel(layout)

        # Segments table
        self._create_table(layout)

    def _create_control_panel(self, parent_layout: QVBoxLayout) -> None:
        """Create the top control panel with filters."""
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(10)

        # Type filter label
        type_label = QLabel("Тип:")
        control_layout.addWidget(type_label)

        # Type filter combo box
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Все", "Attack", "Defense", "Change"])
        self.type_combo.setCurrentText("Все")
        self.type_combo.setFixedWidth(100)
        self.type_combo.currentTextChanged.connect(self._on_filter_changed)
        control_layout.addWidget(self.type_combo)

        # Notes checkbox
        self.notes_checkbox = QCheckBox("Заметки")
        self.notes_checkbox.setChecked(False)
        self.notes_checkbox.stateChanged.connect(self._on_filter_changed)
        control_layout.addWidget(self.notes_checkbox)

        # Reset button
        self.reset_btn = QPushButton("Сброс")
        self.reset_btn.setFixedWidth(80)
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        control_layout.addWidget(self.reset_btn)

        # Add stretch to push controls to the left
        control_layout.addStretch()

        parent_layout.addWidget(control_panel)

    def _create_table(self, parent_layout: QVBoxLayout) -> None:
        """Create the segments table."""
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Начало", "Конец", "Длит.", "Действия"])

        # Configure table appearance
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Configure headers
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Название
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Начало
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Конец
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Длит.
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Действия

        # Set column widths
        self.table.setColumnWidth(0, 40)   # ID
        self.table.setColumnWidth(2, 60)   # Начало
        self.table.setColumnWidth(3, 60)   # Конец
        self.table.setColumnWidth(4, 70)   # Длит.
        self.table.setColumnWidth(5, 100)  # Действия

        # Set row height
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.verticalHeader().setVisible(False)

        parent_layout.addWidget(self.table)

    def _on_filter_changed(self) -> None:
        """Handle filter changes."""
        self.update_segments(self.segments)

    def _on_reset_clicked(self) -> None:
        """Handle reset button click."""
        self.type_combo.setCurrentText("Все")
        self.notes_checkbox.setChecked(False)
        self.update_segments(self.segments)

    def update_segments(self, segments: List[Marker]) -> None:
        """Update the segments table with new data.

        Args:
            segments: List of Marker objects to display
        """
        self.segments = segments

        # Apply filters
        filtered_segments = self._apply_filters(segments)

        # Clear and repopulate table
        self.table.setRowCount(0)

        for row_idx, segment in enumerate(filtered_segments):
            self.table.insertRow(row_idx)

            # Column 0: ID
            id_item = QTableWidgetItem(str(row_idx + 1))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 0, id_item)

            # Column 1: Название (Event name)
            name_item = QTableWidgetItem(segment.event_name)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 1, name_item)

            # Column 2: Начало (Start time)
            start_time = self._format_time(segment.start_frame / self.fps)
            start_item = QTableWidgetItem(start_time)
            start_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 2, start_item)

            # Column 3: Конец (End time)
            end_time = self._format_time(segment.end_frame / self.fps)
            end_item = QTableWidgetItem(end_time)
            end_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 3, end_item)

            # Column 4: Длит. (Duration)
            duration_frames = segment.end_frame - segment.start_frame
            duration_time = self._format_time(duration_frames / self.fps)
            duration_item = QTableWidgetItem(duration_time)
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, 4, duration_item)

            # Column 5: Действия (Actions)
            actions_widget = self._create_actions_widget(row_idx)
            self.table.setCellWidget(row_idx, 5, actions_widget)

    def _apply_filters(self, segments: List[Marker]) -> List[Marker]:
        """Apply current filters to the segments list.

        Args:
            segments: Original segments list

        Returns:
            Filtered segments list
        """
        filtered = segments.copy()

        # Type filter
        selected_type = self.type_combo.currentText()
        if selected_type != "Все":
            filtered = [s for s in filtered if s.event_name == selected_type]

        # Notes filter
        if self.notes_checkbox.isChecked():
            filtered = [s for s in filtered if s.note.strip()]

        return filtered

    def _create_actions_widget(self, row_idx: int) -> QWidget:
        """Create action buttons widget for a table row.

        Args:
            row_idx: Row index in the table

        Returns:
            QWidget containing action buttons
        """
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Edit button
        edit_btn = QPushButton("✏")
        edit_btn.setFixedSize(25, 25)
        edit_btn.setToolTip("Редактировать")
        edit_btn.clicked.connect(lambda: self._on_edit_clicked(row_idx))
        layout.addWidget(edit_btn)

        # Delete button
        delete_btn = QPushButton("🗑")
        delete_btn.setFixedSize(25, 25)
        delete_btn.setToolTip("Удалить")
        delete_btn.clicked.connect(lambda: self._on_delete_clicked(row_idx))
        layout.addWidget(delete_btn)

        layout.addStretch()
        return widget

    def _on_edit_clicked(self, row_idx: int) -> None:
        """Handle edit button click.

        Args:
            row_idx: Row index that was clicked
        """
        # Get the actual segment index from filtered results
        filtered_segments = self._apply_filters(self.segments)
        if 0 <= row_idx < len(filtered_segments):
            segment = filtered_segments[row_idx]
            original_idx = self.segments.index(segment)
            print(f"Edit segment at index {original_idx}: {segment}")

    def _on_delete_clicked(self, row_idx: int) -> None:
        """Handle delete button click.

        Args:
            row_idx: Row index that was clicked
        """
        # Get the actual segment index from filtered results
        filtered_segments = self._apply_filters(self.segments)
        if 0 <= row_idx < len(filtered_segments):
            segment = filtered_segments[row_idx]
            original_idx = self.segments.index(segment)
            print(f"Delete segment at index {original_idx}: {segment}")

    def _format_time(self, seconds: float) -> str:
        """Format time as MM:SS.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string
        """
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    def set_fps(self, fps: float) -> None:
        """Set the FPS for time formatting.

        Args:
            fps: Frames per second
        """
        self.fps = fps
        self.update_segments(self.segments)

    def clear_segments(self) -> None:
        """Clear all segments from the table."""
        self.segments = []
        self.table.setRowCount(0)

    def _connect_signals(self) -> None:
        """Connect signals if filter controller is available."""
        if self.filter_controller:
            self.filter_controller.filters_changed.connect(self._on_external_filters_changed)

    def _on_external_filters_changed(self) -> None:
        """Handle external filter changes."""
        # Update the UI to reflect external filter changes
        # This will be called when filters change from other parts of the app
        self.update_segments(self.segments)

    def get_filtered_segments(self) -> List[Marker]:
        """Get the currently filtered segments.

        Returns:
            List of filtered Marker objects
        """
        return self._apply_filters(self.segments)
