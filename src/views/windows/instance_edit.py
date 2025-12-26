"""
Instance Edit Window - Modal dialog for precise segment editing.

Provides interface for editing video segment boundaries, event type, and notes.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.marker import Marker
except ImportError:
    # Для случаев, когда запускаем из src/
    from ...models.domain.marker import Marker


class InstanceEditWindow(QDialog):
    """Modal dialog for editing video segments."""

    # Signals
    previous_requested = Signal()
    next_requested = Signal()
    save_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.marker: Optional[Marker] = None
        self.fps: float = 30.0
        self.total_frames: int = 0

        self.setWindowTitle("Instance Edit")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Video preview (top section)
        self._create_video_preview(layout)

        # Timeline editing section
        self._create_timeline_section(layout)

        # Trim controls
        self._create_trim_controls(layout)

        # Data editing section
        self._create_data_section(layout)

        # Footer buttons
        self._create_footer(layout)

    def _create_video_preview(self, parent_layout: QVBoxLayout) -> None:
        """Create video preview section."""
        # Video display placeholder
        self.video_label = QLabel("Video Preview")
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #000000;
                color: #666666;
                border: 2px solid #444444;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        parent_layout.addWidget(self.video_label, stretch=1)

    def _create_timeline_section(self, parent_layout: QVBoxLayout) -> None:
        """Create timeline editing section with progress bar and time labels."""
        # Time labels layout
        time_layout = QHBoxLayout()

        self.start_time_label = QLabel("00:00")
        self.start_time_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        time_layout.addWidget(self.start_time_label)

        time_layout.addStretch()

        self.end_time_label = QLabel("00:00")
        self.end_time_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        time_layout.addWidget(self.end_time_label)

        parent_layout.addLayout(time_layout)

        # Timeline progress bar (placeholder for dual-handle slider)
        self.timeline_bar = QProgressBar()
        self.timeline_bar.setRange(0, 100)
        self.timeline_bar.setValue(50)
        self.timeline_bar.setTextVisible(False)
        self.timeline_bar.setFixedHeight(20)
        self.timeline_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #444444;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #1a4d7a;
                border-radius: 3px;
            }
        """)
        parent_layout.addWidget(self.timeline_bar)

        # Note about dual handles
        handles_note = QLabel("Note: Dual-handle slider would be implemented here")
        handles_note.setStyleSheet("color: #888888; font-style: italic;")
        parent_layout.addWidget(handles_note)

    def _create_trim_controls(self, parent_layout: QVBoxLayout) -> None:
        """Create trim controls with IN/OUT buttons and play loop."""
        controls_layout = QHBoxLayout()

        # IN group
        in_group = QFrame()
        in_group.setFrameStyle(QFrame.Shape.Box)
        in_layout = QHBoxLayout(in_group)
        in_layout.setContentsMargins(5, 5, 5, 5)
        in_layout.setSpacing(2)

        in_label = QLabel("IN")
        in_label.setStyleSheet("font-weight: bold;")
        in_layout.addWidget(in_label)

        self.in_minus_btn = QPushButton("-1")
        self.in_minus_btn.setFixedWidth(30)
        self.in_minus_btn.clicked.connect(self._on_in_minus)
        in_layout.addWidget(self.in_minus_btn)

        self.set_in_btn = QPushButton("SET IN")
        self.set_in_btn.clicked.connect(self._on_set_in)
        in_layout.addWidget(self.set_in_btn)

        self.in_plus_btn = QPushButton("+1")
        self.in_plus_btn.setFixedWidth(30)
        self.in_plus_btn.clicked.connect(self._on_in_plus)
        in_layout.addWidget(self.in_plus_btn)

        controls_layout.addWidget(in_group)

        controls_layout.addStretch()

        # Play Loop button (center)
        self.play_loop_btn = QPushButton("Play Loop")
        self.play_loop_btn.setFixedWidth(100)
        self.play_loop_btn.clicked.connect(self._on_play_loop)
        controls_layout.addWidget(self.play_loop_btn)

        controls_layout.addStretch()

        # OUT group
        out_group = QFrame()
        out_group.setFrameStyle(QFrame.Shape.Box)
        out_layout = QHBoxLayout(out_group)
        out_layout.setContentsMargins(5, 5, 5, 5)
        out_layout.setSpacing(2)

        out_label = QLabel("OUT")
        out_label.setStyleSheet("font-weight: bold;")
        out_layout.addWidget(out_label)

        self.out_minus_btn = QPushButton("-1")
        self.out_minus_btn.setFixedWidth(30)
        self.out_minus_btn.clicked.connect(self._on_out_minus)
        out_layout.addWidget(self.out_minus_btn)

        self.set_out_btn = QPushButton("SET OUT")
        self.set_out_btn.clicked.connect(self._on_set_out)
        out_layout.addWidget(self.set_out_btn)

        self.out_plus_btn = QPushButton("+1")
        self.out_plus_btn.setFixedWidth(30)
        self.out_plus_btn.clicked.connect(self._on_out_plus)
        out_layout.addWidget(self.out_plus_btn)

        controls_layout.addWidget(out_group)

        parent_layout.addLayout(controls_layout)

    def _create_data_section(self, parent_layout: QVBoxLayout) -> None:
        """Create data editing section with event type and notes."""
        data_layout = QHBoxLayout()

        # Event type (Code)
        data_layout.addWidget(QLabel("Code:"))

        self.event_combo = QComboBox()
        self.event_combo.addItems(["Attack", "Defense", "Change"])
        self.event_combo.setFixedWidth(120)
        self.event_combo.currentTextChanged.connect(self._on_event_changed)
        data_layout.addWidget(self.event_combo)

        data_layout.addStretch()

        # Notes
        data_layout.addWidget(QLabel("Note:"))

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Enter note...")
        self.note_edit.textChanged.connect(self._on_note_changed)
        data_layout.addWidget(self.note_edit)

        parent_layout.addLayout(data_layout)

    def _create_footer(self, parent_layout: QVBoxLayout) -> None:
        """Create footer with navigation and save buttons."""
        footer_layout = QHBoxLayout()

        # Previous button
        self.previous_btn = QPushButton("Previous")
        self.previous_btn.clicked.connect(self._on_previous)
        footer_layout.addWidget(self.previous_btn)

        footer_layout.addStretch()

        # Save button (green styling)
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #00AA00;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #008800;
            }
            QPushButton:pressed {
                background-color: #006600;
            }
        """)
        self.save_btn.clicked.connect(self._on_save)
        footer_layout.addWidget(self.save_btn)

        footer_layout.addStretch()

        # Next button
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self._on_next)
        footer_layout.addWidget(self.next_btn)

        parent_layout.addLayout(footer_layout)

    # Event handlers
    def _on_in_minus(self) -> None:
        """Handle IN minus button."""
        if self.marker:
            self.marker.start_frame = max(0, self.marker.start_frame - 1)
            self._update_ui()

    def _on_set_in(self) -> None:
        """Handle SET IN button."""
        # Placeholder - would set IN point to current playback position
        print("SET IN clicked")

    def _on_in_plus(self) -> None:
        """Handle IN plus button."""
        if self.marker:
            self.marker.start_frame = min(self.marker.end_frame - 1, self.marker.start_frame + 1)
            self._update_ui()

    def _on_out_minus(self) -> None:
        """Handle OUT minus button."""
        if self.marker:
            self.marker.end_frame = max(self.marker.start_frame + 1, self.marker.end_frame - 1)
            self._update_ui()

    def _on_set_out(self) -> None:
        """Handle SET OUT button."""
        # Placeholder - would set OUT point to current playback position
        print("SET OUT clicked")

    def _on_out_plus(self) -> None:
        """Handle OUT plus button."""
        if self.marker:
            self.marker.end_frame = min(self.total_frames, self.marker.end_frame + 1)
            self._update_ui()

    def _on_play_loop(self) -> None:
        """Handle Play Loop button."""
        # Placeholder - would start/stop loop playback
        print("Play Loop clicked")

    def _on_event_changed(self, event_name: str) -> None:
        """Handle event type change."""
        if self.marker:
            self.marker.event_name = event_name

    def _on_note_changed(self, note: str) -> None:
        """Handle note change."""
        if self.marker:
            self.marker.note = note

    def _on_previous(self) -> None:
        """Handle Previous button."""
        self.previous_requested.emit()

    def _on_save(self) -> None:
        """Handle Save button."""
        self.save_requested.emit()
        self.accept()

    def _on_next(self) -> None:
        """Handle Next button."""
        self.next_requested.emit()

    def _update_ui(self) -> None:
        """Update UI elements based on current marker data."""
        if not self.marker:
            return

        # Update time labels
        start_seconds = self.marker.start_frame / self.fps
        end_seconds = self.marker.end_frame / self.fps

        self.start_time_label.setText("02d")
        self.end_time_label.setText("02d")

        # Update progress bar (simplified representation)
        if self.total_frames > 0:
            progress = int((self.marker.start_frame + self.marker.end_frame) / 2 / self.total_frames * 100)
            self.timeline_bar.setValue(progress)

        # Update event combo
        index = self.event_combo.findText(self.marker.event_name)
        if index >= 0:
            self.event_combo.setCurrentIndex(index)

        # Update note
        self.note_edit.setText(self.marker.note)

    # Public methods
    def load_marker(self, marker: Marker) -> None:
        """Load marker data into the dialog.

        Args:
            marker: Marker object to edit
        """
        self.marker = marker
        self._update_ui()

    def get_result(self) -> Optional[Marker]:
        """Get the edited marker result.

        Returns:
            Updated Marker object or None if cancelled
        """
        return self.marker

    def set_video_fps(self, fps: float) -> None:
        """Set video FPS for time calculations.

        Args:
            fps: Frames per second
        """
        self.fps = fps
        self._update_ui()

    def set_total_frames(self, total_frames: int) -> None:
        """Set total video frames.

        Args:
            total_frames: Total number of frames in video
        """
        self.total_frames = total_frames

    def set_video_image(self, pixmap: QPixmap) -> None:
        """Set video preview image.

        Args:
            pixmap: Video frame pixmap
        """
        self.video_label.setPixmap(pixmap)
