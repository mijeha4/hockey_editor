"""
Timeline Scene Widget - Multi-track timeline for hockey events.

Displays vertical tracks for different event types (Blocked, Blockshot, Faceoff, Goal, etc.)
with horizontal time ruler, red current time line, and colored event rectangles.
"""

from typing import List, Optional, Dict
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsLineItem, QGraphicsPolygonItem, QFrame
)
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter, QPolygonF
from PySide6.QtCore import Qt, QRectF, QPointF, Signal

# Import project dependencies
try:
    from views.styles import AppColors
    from models.domain.marker import Marker
except ImportError:
    # For compatibility with run_test.py
    from ..styles import AppColors
    from ...models.domain.marker import Marker


class EventItem(QGraphicsRectItem):
    """Rectangle item representing an event on a track."""

    # Color mapping for hockey events
    EVENT_COLORS = {
        "Гол": QColor(255, 100, 100),  # Red for goals
        "Бросок в створ": QColor(100, 150, 255),  # Blue
        "Бросок мимо": QColor(150, 150, 150),  # Gray
        "Удаление": QColor(255, 200, 100),  # Orange
        "Вброс": QColor(100, 255, 100),  # Green
        "Перехват": QColor(200, 100, 255),  # Purple
        "Блокшот": QColor(255, 150, 50),  # Brown/orange
        "Блокшот в обороне": QColor(255, 150, 50),
        "Вбрасывание: Проиграно": QColor(255, 100, 100),
        "Вбрасывание: Пропущено": QColor(100, 255, 100),
        "Потеря": QColor(200, 200, 100),  # Yellow
        "Вход в зону": QColor(150, 200, 255),  # Light blue
        "Выход из зоны": QColor(150, 200, 255),
        "Заблокировано": QColor(100, 100, 150),  # Dark blue
    }

    def __init__(self, marker: Marker, track_index: int, pixels_per_second: float,
                 track_height: int, ruler_height: int, fps: float = 30.0, parent=None):
        super().__init__(parent)
        self.marker = marker
        self.track_index = track_index
        self.pixels_per_second = pixels_per_second
        self.track_height = track_height
        self.ruler_height = ruler_height
        self.fps = fps
        self.is_selected = False

        # Calculate position and size
        start_sec = marker.start_frame / fps
        duration_sec = (marker.end_frame - marker.start_frame) / fps
        y = ruler_height + track_index * track_height + 4
        x = start_sec * pixels_per_second
        w = max(duration_sec * pixels_per_second, 12)  # Minimum width 12px
        h = track_height - 8

        self.setRect(x, y, w, h)

        # Get color
        self.normal_color = self._get_event_color(marker)
        self.hover_color = self.normal_color.lighter(120)
        self.selected_color = self.normal_color.lighter(150)

        # Semi-transparent fill
        color_with_alpha = QColor(self.normal_color)
        color_with_alpha.setAlpha(180)
        self.setBrush(QBrush(color_with_alpha))
        self.setPen(QPen(QColor(60, 60, 60), 1))

        # Add label
        self._add_label(marker, x, y, w, h)

    def _add_label(self, marker: Marker, x: float, y: float, w: float, h: float):
        """Add text label to the event."""
        # Use note if available, otherwise event name
        label_text = marker.note if marker.note else marker.event_name[:10]

        text = QGraphicsTextItem(label_text, self)
        text.setDefaultTextColor(Qt.white)
        text.setFont(QFont("Segoe UI", 8))

        # Position text inside the rectangle
        text.setPos(x + 2, y + 2)

        # Ensure text fits
        text_rect = text.boundingRect()
        if text_rect.width() > w - 4:
            # Truncate if too long
            while text_rect.width() > w - 4 and len(label_text) > 3:
                label_text = label_text[:-1]
                text.setPlainText(label_text + "...")
                text_rect = text.boundingRect()

        # Enable hover events
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        """Handle mouse hover enter."""
        if not self.is_selected:
            self.setBrush(QBrush(self.hover_color))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """Handle mouse hover leave."""
        if not self.is_selected:
            self.setBrush(QBrush(self.normal_color))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press for selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_selected(not self.is_selected)
            # Emit signal for selection
            if hasattr(self.scene(), 'event_selected'):
                self.scene().event_selected.emit(self.marker)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle double click for editing."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Emit signal for editing
            if hasattr(self.scene(), 'event_double_clicked'):
                self.scene().event_double_clicked.emit(self.marker)
        super().mouseDoubleClickEvent(event)

    def set_selected(self, selected: bool):
        """Set selection state."""
        self.is_selected = selected
        if selected:
            self.setBrush(QBrush(self.selected_color))
            self.setPen(QPen(QColor(255, 255, 255), 2))
        else:
            self.setBrush(QBrush(self.normal_color))
            self.setPen(QPen(QColor(60, 60, 60), 1))

    def _get_event_color(self, marker: Marker) -> QColor:
        """Get color for event type."""
        # Check if marker has custom display color
        if hasattr(marker, '_display_color') and marker._display_color:
            return marker._display_color

        # Try event manager first
        try:
            from services.events.custom_event_manager import get_custom_event_manager
            event_manager = get_custom_event_manager()
            if event_manager:
                event = event_manager.get_event(marker.event_name)
                if event:
                    return QColor(event.color)
        except ImportError:
            pass

        # Use predefined colors
        return self.EVENT_COLORS.get(marker.event_name, QColor(100, 100, 200))  # Default blue


class TimelineScene(QGraphicsScene):
    """Graphics scene managing timeline elements."""

    # Signals
    seek_requested = Signal(int)  # Frame number to seek to
    event_double_clicked = Signal(object)  # Marker object for editing
    event_selected = Signal(object)  # Marker object selected

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QColor(AppColors.ELEMENT_BG))

        # Timeline parameters
        self.pixels_per_second = 10.0  # Scale: 1 sec = 10 pixels
        self.track_height = 28
        self.ruler_height = 40
        self.fps = 30.0  # Frames per second

        # Data
        self.tracks = []  # List of track names
        self.markers = []  # List of Marker objects
        self.event_items = []  # Graphics items for events

        # Graphics items
        self.current_time_line = None
        self.ruler_items = []
        self.track_background_items = []
        self.track_header_items = []

    def set_tracks(self, track_names: List[str]):
        """Set the list of track names (event types)."""
        self.tracks = track_names
        self.rebuild()

    def set_markers(self, markers: List[Marker]):
        """Set markers to display on timeline."""
        self.markers = markers
        self.rebuild()

    def add_event(self, track_name: str, start_sec: float, duration_sec: float, label: str = "", color: QColor = None):
        """Add a single event to the timeline."""
        # Create a temporary marker for display
        from models.domain.marker import Marker
        marker = Marker(
            start_frame=int(start_sec * self.fps),
            end_frame=int((start_sec + duration_sec) * self.fps),
            event_name=track_name,
            note=label
        )

        # Override color if provided
        if color:
            # Store color in marker temporarily (this is a hack, but works for display)
            marker._display_color = color

        self.markers.append(marker)
        self._draw_single_event(marker)

    def set_duration(self, total_seconds: float):
        """Set total duration and update scene size."""
        w = total_seconds * self.pixels_per_second + 200  # Extra space
        h = len(self.tracks) * self.track_height + self.ruler_height + 20
        self.setSceneRect(0, 0, w, h)

    def rebuild(self):
        """Rebuild all timeline elements."""
        self.clear()

        # Create graphics items lists
        self.event_items = []
        self.ruler_items = []
        self.track_background_items = []
        self.track_header_items = []

        # Draw track backgrounds and headers
        self._draw_tracks()

        # Draw ruler
        self._draw_ruler()

        # Draw events
        self._draw_events()

        # Draw current time line
        self._draw_current_time_line()

    def _draw_tracks(self):
        """Draw track backgrounds and headers."""
        for i, track_name in enumerate(self.tracks):
            y = self.ruler_height + i * self.track_height

            # Track background
            bg = QGraphicsRectItem(0, y, self.sceneRect().width(), self.track_height - 1)
            bg.setBrush(QColor(36, 36, 36) if i % 2 == 0 else QColor(32, 32, 32))
            bg.setPen(QPen(Qt.NoPen))
            self.addItem(bg)
            self.track_background_items.append(bg)

            # Yellow header stripe (only for "Гол" as per description)
            if "Гол" in track_name:
                header_bg = QGraphicsRectItem(0, y, 140, self.track_height - 1)
                header_bg.setBrush(QColor(180, 140, 0, 180))
                header_bg.setPen(QPen(Qt.NoPen))
                self.addItem(header_bg)
                self.track_header_items.append(header_bg)

            # Track name text
            text = QGraphicsTextItem(track_name, None)
            text.setDefaultTextColor(QColor(220, 220, 220))
            text.setFont(QFont("Segoe UI", 10))
            text.setPos(8, y + 4)
            self.addItem(text)

    def _draw_ruler(self):
        """Draw horizontal time ruler."""
        # Ruler background
        ruler_bg = self.addRect(0, 0, self.sceneRect().width(), self.ruler_height,
                                QPen(Qt.NoPen), QBrush(QColor(AppColors.BACKGROUND)))

        # Time marks every 5 seconds
        font = QFont("Segoe UI", 9)
        for sec in range(0, int(self.sceneRect().width() / self.pixels_per_second) + 1, 5):
            x = sec * self.pixels_per_second

            # Major tick every 10 seconds
            h = 12 if sec % 10 == 0 else 8
            tick = QGraphicsLineItem(x, self.ruler_height - h, x, self.ruler_height)
            tick.setPen(QPen(QColor(160, 160, 160), 1))
            self.addItem(tick)
            self.ruler_items.append(tick)

            # Time text every 5 seconds
            if sec % 5 == 0:
                time_text = f"{sec//60:02d}:{sec%60:02d}"
                text_item = QGraphicsTextItem(time_text, None)
                text_item.setDefaultTextColor(QColor(200, 200, 200))
                text_item.setFont(font)
                text_item.setPos(x - 20, 12)
                self.addItem(text_item)
                self.ruler_items.append(text_item)

    def _draw_events(self):
        """Draw event rectangles on tracks."""
        for marker in self.markers:
            self._draw_single_event(marker)

    def _draw_single_event(self, marker: Marker):
        """Draw a single event on the timeline."""
        # Find track index for this event type
        try:
            track_index = self.tracks.index(marker.event_name)
        except ValueError:
            return  # Skip if track not found

        # Create event item
        event_item = EventItem(marker, track_index, self.pixels_per_second,
                             self.track_height, self.ruler_height, self.fps)
        self.addItem(event_item)
        self.event_items.append(event_item)

    def _draw_current_time_line(self):
        """Draw red vertical current time line with marker."""
        # Main line
        self.current_time_line = QGraphicsLineItem(0, 0, 0, self.sceneRect().height())
        self.current_time_line.setPen(QPen(QColor(220, 30, 30), 1, Qt.DashLine))
        self.addItem(self.current_time_line)

        # Yellow triangle marker at the top
        triangle = QGraphicsPolygonItem()
        triangle.setPolygon(QPolygonF([
            QPointF(-4, self.ruler_height),
            QPointF(4, self.ruler_height),
            QPointF(0, self.ruler_height + 8)
        ]))
        triangle.setBrush(QBrush(QColor(255, 255, 0)))  # Yellow
        triangle.setPen(QPen(Qt.NoPen))
        self.addItem(triangle)
        self.current_time_marker = triangle

    def set_current_time(self, seconds: float):
        """Update current time line position."""
        if self.current_time_line:
            x = seconds * self.pixels_per_second
            self.current_time_line.setLine(x, 0, x, self.sceneRect().height())
            if hasattr(self, 'current_time_marker'):
                self.current_time_marker.setPos(x, 0)

    def set_fps(self, fps: float):
        """Set frames per second for time calculations."""
        self.fps = fps

    def get_pixels_per_second(self) -> float:
        """Get current pixels per second scale."""
        return self.pixels_per_second

    def set_zoom(self, pixels_per_second: float):
        """Set zoom level (pixels per second)."""
        self.pixels_per_second = max(5.0, min(20.0, pixels_per_second))
        self.rebuild()


class TimelineWidget(QGraphicsView):
    """Graphics view widget for the timeline."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.scene = TimelineScene(self)
        self.setScene(self.scene)

        # Connect signals
        self.scene.seek_requested.connect(self._on_seek_requested)

    def init_tracks(self, track_names: List[str], total_frames: int, fps: float = 30.0):
        """Initialize timeline with tracks and duration."""
        self.scene.set_fps(fps)
        self.scene.set_tracks(track_names)
        total_sec = total_frames / fps
        self.scene.set_duration(total_sec)

    def set_markers(self, markers: List[Marker]):
        """Set markers to display."""
        self.scene.set_markers(markers)

    def set_current_frame(self, frame: int, fps: float = 30.0):
        """Update current time position."""
        sec = frame / fps
        self.scene.set_current_time(sec)

    def set_zoom(self, pixels_per_second: float):
        """Set zoom level."""
        self.scene.set_zoom(pixels_per_second)

    def rebuild(self, animate_new: bool = True):
        """Rebuild the timeline scene (for compatibility)."""
        self.scene.rebuild()

    def set_total_frames(self, total_frames: int):
        """Set total frames (for compatibility)."""
        # Recalculate duration
        total_sec = total_frames / self.scene.fps
        self.scene.set_duration(total_sec)

    def set_fps(self, fps: float):
        """Set FPS (for compatibility)."""
        self.scene.set_fps(fps)

    def wheelEvent(self, event) -> None:
        """Handle mouse wheel events for zooming."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Zoom in/out
            zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8

            # Update scale
            old_zoom = self.scene.pixels_per_second
            self.set_zoom(old_zoom * zoom_factor)

            # Center on mouse position
            mouse_pos = self.mapToScene(event.pos())
            self.centerOn(mouse_pos)

            event.accept()
        else:
            # Default scrolling behavior
            super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Convert click position to scene coordinates
            scene_pos = self.mapToScene(event.pos())

            # Check if click is on the ruler (top area)
            if scene_pos.y() <= self.scene.ruler_height:
                # Convert X position to frame number
                frame = int(scene_pos.x() / self.scene.pixels_per_second * self.scene.fps)
                frame = max(0, frame)

                # Emit seek signal
                self.scene.seek_requested.emit(frame)

        super().mousePressEvent(event)

    def _on_seek_requested(self, frame: int):
        """Handle seek request from scene."""
        # This will be connected to controller
        pass