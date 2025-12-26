"""
Timeline Widget - Interactive timeline view for video editing.

Displays video timeline with segments, ruler, and playhead.
Supports zooming and seeking functionality.
"""

from typing import List, Optional
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter

# Используем абсолютные импорты для совместимости с run_test.py
try:
    from views.styles import AppColors
    from models.domain.marker import Marker
except ImportError:
    # Для случаев, когда запускаем из src/
    from ..styles import AppColors
    from ...models.domain.marker import Marker


class TimelineWidget(QGraphicsView):
    """Interactive timeline widget for video editing."""

    # Signals
    seek_requested: Signal = Signal(int)  # Frame number to seek to

    def __init__(self, parent: Optional[QGraphicsView] = None) -> None:
        super().__init__(parent)

        # Initialize graphics scene
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QBrush(QColor(AppColors.ELEMENT_BG)))
        self.setScene(self.scene)

        # Timeline parameters
        self.pixels_per_frame: float = 0.8  # Default zoom level
        self.track_height: int = 40  # Height of each track
        self.ruler_height: int = 30  # Height of the ruler
        self.fps: float = 30.0  # Frames per second

        # Graphics items
        self.playhead: Optional[QGraphicsLineItem] = None
        self.segment_items: List[QGraphicsRectItem] = []
        self.ruler_items: List[QGraphicsLineItem] = []
        self.ruler_text_items: List[QGraphicsTextItem] = []

        # Configure view
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # Initialize timeline
        self._setup_timeline()

    def _setup_timeline(self) -> None:
        """Initialize the timeline layout."""
        # Draw initial ruler
        self.draw_ruler()

        # Set initial scene size
        self.scene.setSceneRect(0, 0, 1000, 200)

    def draw_ruler(self) -> None:
        """Draw the time ruler at the top of the timeline."""
        # Clear existing ruler items
        for item in self.ruler_items + self.ruler_text_items:
            self.scene.removeItem(item)
        self.ruler_items.clear()
        self.ruler_text_items.clear()

        # Ruler background
        ruler_bg = self.scene.addRect(0, 0, self.scene.width(), self.ruler_height,
                                    QPen(Qt.PenStyle.NoPen),
                                    QBrush(QColor(AppColors.BACKGROUND)))

        # Draw time marks every 5 seconds
        if self.fps > 0:
            current_time = 0
            while True:
                frame = int(current_time * self.fps)
                x_pos = frame * self.pixels_per_frame

                # Stop if we're beyond the visible area
                if x_pos > self.scene.width():
                    break

                # Major tick (every 5 seconds)
                if current_time % 5 == 0:
                    # Draw tick mark
                    tick = self.scene.addLine(x_pos, self.ruler_height - 10,
                                           x_pos, self.ruler_height,
                                           QPen(QColor(AppColors.TEXT), 2))
                    self.ruler_items.append(tick)

                    # Draw time text
                    time_text = f"{int(current_time // 60):02d}:{int(current_time % 60):02d}"
                    text_item = self.scene.addText(time_text)
                    text_item.setDefaultTextColor(QColor(AppColors.TEXT))
                    text_item.setFont(QFont("Segoe UI", 8))
                    text_item.setPos(x_pos - 15, 5)
                    self.ruler_text_items.append(text_item)

                # Minor tick (every second)
                elif current_time % 1 == 0:
                    tick = self.scene.addLine(x_pos, self.ruler_height - 5,
                                           x_pos, self.ruler_height,
                                           QPen(QColor(AppColors.BORDER), 1))
                    self.ruler_items.append(tick)

                current_time += 1

    def draw_playhead(self, frame: int) -> None:
        """Draw or update the playhead at the specified frame."""
        x_pos = frame * self.pixels_per_frame

        # Remove existing playhead
        if self.playhead:
            self.scene.removeItem(self.playhead)

        # Create new playhead
        self.playhead = self.scene.addLine(x_pos, 0, x_pos, self.scene.height(),
                                        QPen(QColor("#FFFF00"), 3))  # Yellow playhead

        # Bring playhead to front
        if self.playhead:
            self.playhead.setZValue(1000)

    def set_segments(self, segments: List[Marker]) -> None:
        """Set the segments to display on the timeline.

        Args:
            segments: List of Marker objects representing video segments
        """
        # Clear existing segments
        for item in self.segment_items:
            self.scene.removeItem(item)
        self.segment_items.clear()

        # Group segments by event type for tracks
        event_tracks = {}
        track_index = 0

        # Import event manager to get colors
        try:
            from hockey_editor.utils.custom_events import get_custom_event_manager
            event_manager = get_custom_event_manager()
        except ImportError:
            event_manager = None

        # Process each segment
        for segment in segments:
            event_name = segment.event_name

            # Get or create track for this event type
            if event_name not in event_tracks:
                event_tracks[event_name] = track_index
                track_index += 1

            track_y = self.ruler_height + (event_tracks[event_name] * self.track_height)

            # Calculate segment position and size
            start_x = segment.start_frame * self.pixels_per_frame
            width = (segment.end_frame - segment.start_frame + 1) * self.pixels_per_frame
            if width < 5:  # Minimum width
                width = 5

            # Create rectangle for segment
            rect_item = QGraphicsRectItem(start_x, track_y + 5, width, self.track_height - 10)

            # Set color based on event type
            segment_color = QColor(AppColors.ACCENT)  # Default color
            if event_manager:
                event = event_manager.get_event(event_name)
                if event:
                    segment_color = QColor(event.color)

            # Semi-transparent fill
            segment_color.setAlpha(180)
            rect_item.setBrush(QBrush(segment_color))
            rect_item.setPen(QPen(QColor(AppColors.TEXT), 1))

            # Add tooltip
            rect_item.setToolTip(f"{event_name}: {segment.start_frame}-{segment.end_frame}")

            # Add to scene
            self.scene.addItem(rect_item)
            self.segment_items.append(rect_item)

        # Update scene height based on number of tracks
        scene_height = self.ruler_height + (len(event_tracks) * self.track_height) + 20
        current_rect = self.scene.sceneRect()
        self.scene.setSceneRect(0, 0, max(current_rect.width(), 1000), scene_height)

        # Redraw ruler and playhead
        self.draw_ruler()
        if self.playhead:
            self.draw_playhead(int(self.playhead.line().x1() / self.pixels_per_frame))

    def mousePressEvent(self, event) -> None:
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Convert click position to scene coordinates
            scene_pos = self.mapToScene(event.pos())

            # Check if click is on the ruler (top area)
            if scene_pos.y() <= self.ruler_height:
                # Convert X position to frame number
                frame = int(scene_pos.x() / self.pixels_per_frame)
                frame = max(0, frame)  # Ensure non-negative

                # Emit seek signal
                self.seek_requested.emit(frame)

        super().mousePressEvent(event)

    def wheelEvent(self, event) -> None:
        """Handle mouse wheel events for zooming."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Zoom in/out
            zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8

            # Update scale
            self.pixels_per_frame *= zoom_factor

            # Clamp zoom levels
            self.pixels_per_frame = max(0.1, min(5.0, self.pixels_per_frame))

            # Update display
            self.set_segments([])  # This will trigger redraw of everything
            self.draw_ruler()

            # Center on current playhead position if it exists
            if self.playhead:
                current_frame = int(self.playhead.line().x1() / (self.pixels_per_frame / zoom_factor))
                self.draw_playhead(current_frame)

                # Auto-scroll to keep playhead visible
                playhead_x = current_frame * self.pixels_per_frame
                viewport_width = self.viewport().width()
                scroll_x = playhead_x - viewport_width // 2
                self.horizontalScrollBar().setValue(max(0, int(scroll_x)))

            event.accept()
        else:
            # Default scrolling behavior
            super().wheelEvent(event)

    def set_fps(self, fps: float) -> None:
        """Set the frames per second for time calculations.

        Args:
            fps: Frames per second
        """
        self.fps = fps
        self.draw_ruler()

    def get_pixels_per_frame(self) -> float:
        """Get current pixels per frame ratio.

        Returns:
            Current zoom level
        """
        return self.pixels_per_frame

    def set_zoom(self, pixels_per_frame: float) -> None:
        """Set the zoom level.

        Args:
            pixels_per_frame: New pixels per frame ratio
        """
        self.pixels_per_frame = max(0.1, min(5.0, pixels_per_frame))
        self.set_segments([])  # Trigger redraw
        self.draw_ruler()

    def clear_timeline(self) -> None:
        """Clear all segments from the timeline."""
        for item in self.segment_items:
            self.scene.removeItem(item)
        self.segment_items.clear()

        # Reset scene size
        self.scene.setSceneRect(0, 0, 1000, self.ruler_height + 20)

    def set_total_frames(self, total_frames: int) -> None:
        """Set the total number of frames in the video."""
        # Update scene width based on total frames
        scene_width = max(1000, total_frames * self.pixels_per_frame)
        current_rect = self.scene.sceneRect()
        self.scene.setSceneRect(0, 0, scene_width, current_rect.height())
        self.draw_ruler()

    def set_fps(self, fps: float) -> None:
        """Set the frames per second for time calculations."""
        self.fps = fps
        self.draw_ruler()
