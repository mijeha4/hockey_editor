"""
Segment List Widget - displays video segments in a card-based list format.

Replaces the simple QListWidget with interactive cards showing:
- Segment number
- Event name (bold, colored)
- Time range (dimmed)
- Action icons on hover (delete, edit, jump to moment)
"""

from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QLabel,
    QPushButton, QSizePolicy, QGraphicsDropShadowEffect
)
from ..models.marker import Marker
from ..utils.custom_events import get_custom_event_manager


class SegmentCard(QFrame):
    """Individual segment card widget."""

    # Signals
    edit_requested = Signal(int)  # marker_idx
    delete_requested = Signal(int)  # marker_idx
    jump_requested = Signal(int)  # marker_idx

    def __init__(self, marker_idx: int, marker: Marker, fps: float, parent=None):
        super().__init__(parent)
        self.marker_idx = marker_idx
        self.marker = marker
        self.fps = fps
        self.event_manager = get_custom_event_manager()
        self.is_hovered = False

        self.setup_ui()
        self.setup_shadow()

    def setup_ui(self):
        """Create the card UI."""
        self.setFixedHeight(50)
        self.setStyleSheet("""
            SegmentCard {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                border-radius: 6px;
            }
            SegmentCard:hover {
                background-color: #333333;
                border-color: #666666;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        # Segment number (small, dimmed)
        self.number_label = QLabel(f"#{self.marker_idx + 1}")
        self.number_label.setStyleSheet("color: #888888; font-size: 10px;")
        self.number_label.setFixedWidth(25)
        layout.addWidget(self.number_label)

        # Event name (bold, colored)
        event = self.event_manager.get_event(self.marker.event_name)
        event_name = event.get_localized_name() if event else self.marker.event_name
        event_color = event.get_qcolor().name() if event else "#ffffff"

        self.event_label = QLabel(event_name)
        self.event_label.setStyleSheet(f"""
            QLabel {{
                color: {event_color};
                font-weight: bold;
                font-size: 12px;
            }}
        """)
        layout.addWidget(self.event_label, 1)  # stretch factor 1

        # Time range (dimmed)
        start_time = self._format_time(self.marker.start_frame / self.fps)
        end_time = self._format_time(self.marker.end_frame / self.fps)
        time_text = f"{start_time}–{end_time}"

        self.time_label = QLabel(time_text)
        self.time_label.setStyleSheet("color: #888888; font-size: 11px;")
        self.time_label.setFixedWidth(80)
        layout.addWidget(self.time_label)

        # Action buttons container (initially hidden)
        self.actions_container = QWidget()
        actions_layout = QHBoxLayout(self.actions_container)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(2)

        # Jump to moment button
        self.jump_btn = QPushButton("🎯")
        self.jump_btn.setFixedSize(24, 24)
        self.jump_btn.setToolTip("Перейти к моменту")
        self.jump_btn.setStyleSheet(self._get_action_button_style())
        self.jump_btn.clicked.connect(lambda: self.jump_requested.emit(self.marker_idx))
        actions_layout.addWidget(self.jump_btn)

        # Edit button
        self.edit_btn = QPushButton("✏️")
        self.edit_btn.setFixedSize(24, 24)
        self.edit_btn.setToolTip("Редактировать")
        self.edit_btn.setStyleSheet(self._get_action_button_style())
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.marker_idx))
        actions_layout.addWidget(self.edit_btn)

        # Delete button
        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.setToolTip("Удалить")
        self.delete_btn.setStyleSheet(self._get_action_button_style())
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.marker_idx))
        actions_layout.addWidget(self.delete_btn)

        layout.addWidget(self.actions_container)

        # Initially hide action buttons
        self.actions_container.setVisible(False)

    def setup_shadow(self):
        """Add subtle shadow effect."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

    def enterEvent(self, event):
        """Show action buttons on hover."""
        self.is_hovered = True
        self.actions_container.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Hide action buttons when not hovering."""
        self.is_hovered = False
        self.actions_container.setVisible(False)
        super().leaveEvent(event)

    def _format_time(self, seconds: float) -> str:
        """Format time as MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    def _get_action_button_style(self) -> str:
        """Get consistent style for action buttons."""
        return """
            QPushButton {
                background-color: transparent;
                border: none;
                color: #cccccc;
                font-size: 12px;
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


class SegmentListWidget(QWidget):
    """Widget for displaying segments in a card-based list."""

    # Signals
    segment_edit_requested = Signal(int)  # marker_idx
    segment_delete_requested = Signal(int)  # marker_idx
    segment_jump_requested = Signal(int)  # marker_idx

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fps = 30.0  # default, will be updated
        self.segments = []  # list of (marker_idx, marker) tuples

        self.setup_ui()

    def setup_ui(self):
        """Create the main UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Scroll area for segments
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2a2a2a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #666666;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #888888;
            }
        """)

        # Container for segment cards
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(4)
        self.cards_layout.addStretch()  # Push cards to top

        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area)

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
        """Refresh all segment cards."""
        # Clear existing cards
        while self.cards_layout.count() > 1:  # Keep the stretch at the end
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create new cards
        for marker_idx, marker in self.segments:
            card = SegmentCard(marker_idx, marker, self.fps)

            # Connect signals
            card.edit_requested.connect(self.segment_edit_requested)
            card.delete_requested.connect(self.segment_delete_requested)
            card.jump_requested.connect(self.segment_jump_requested)

            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)  # Insert before stretch

    def clear_segments(self):
        """Clear all segments."""
        self.segments = []
        self.refresh_segments()
