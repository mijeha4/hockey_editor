"""
Optimized Instance Edit Controller - manages segment editing operations.

Provides optimized timeline updates without ObservableMarker dependency.
Uses direct signal communication for immediate timeline updates.
"""

from typing import Optional, List, Tuple
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QPixmap

# Импорты для работы из корня проекта (main.py добавляет src в sys.path)
try:
    from models.domain.marker import Marker
    from utils.time_utils import frames_to_time
    from utils.custom_events import get_custom_event_manager
except ImportError:
    # Для случаев, когда запускаем из src/
    try:
        from ..models.domain.marker import Marker
        from hockey_editor.utils.time_utils import frames_to_time
        from hockey_editor.utils.custom_events import get_custom_event_manager
    except ImportError:
        # Fallback для тестирования
        from models.domain.marker import Marker
        from hockey_editor.utils.time_utils import frames_to_time
        from hockey_editor.utils.custom_events import get_custom_event_manager


class InstanceEditControllerOptimized(QObject):
    """Optimized controller for managing instance (segment) editing operations."""

    # Signals
    marker_updated = Signal()           # Marker data changed
    marker_saved = Signal()             # Marker saved successfully
    playback_position_changed = Signal(int)  # Current frame changed
    timeline_range_changed = Signal(int, int)  # Start/end frames changed
    active_point_changed = Signal(str)  # 'in' or 'out' point active

    def __init__(self, main_controller, parent=None):
        super().__init__(parent)

        self.main_controller = main_controller
        self.playback_controller = main_controller.playback_controller
        self.video_service = main_controller.video_service
        self.timeline_controller = main_controller.timeline_controller

        # Current marker being edited
        self.marker: Optional[Marker] = None
        self.marker_index: int = -1  # Индекс маркера в списке

        # Navigation state
        self.filtered_markers: List[Tuple[int, Marker]] = []
        self.current_marker_idx = 0

        # Playback state
        self.is_playing = False
        self.loop_enabled = True
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)

        # Editing state
        self.active_point = 'in'  # 'in' or 'out'

        # Video display state
        self.current_frame_pixmap: Optional[QPixmap] = None

    def set_marker(self, marker: Marker, marker_index: int, filtered_markers: List[Tuple[int, Marker]] = None,
                   current_idx: int = 0):
        """Set the marker to edit with its index."""
        self.marker = marker
        self.marker_index = marker_index
        self.filtered_markers = filtered_markers or []
        self.current_marker_idx = current_idx

        # Seek to marker start
        self.playback_controller.seek_to_frame(marker.start_frame)
        self._update_current_frame()

    def get_marker(self) -> Optional[Marker]:
        """Get the current marker."""
        return self.marker

    def get_marker_index(self) -> int:
        """Get the current marker index."""
        return self.marker_index

    def get_fps(self) -> float:
        """Get video FPS."""
        return self.video_service.get_fps() if self.video_service.cap else 30.0

    def get_total_frames(self) -> int:
        """Get total video frames."""
        return self.video_service.get_total_frames()

    # Timeline operations with optimized updates
    def set_timeline_range(self, start_frame: int, end_frame: int):
        """Update marker range from timeline drag with optimized timeline update."""
        if not self.marker:
            return

        # Validate range
        total_frames = self.get_total_frames()
        start_frame = max(0, min(start_frame, total_frames - 1))
        end_frame = max(start_frame + 1, min(end_frame, total_frames))

        self.marker.start_frame = start_frame
        self.marker.end_frame = end_frame

        self.timeline_range_changed.emit(start_frame, end_frame)
        self.marker_updated.emit()

        # Оптимизированное обновление таймлайна
        if self.marker_index >= 0 and self.timeline_controller:
            self.timeline_controller.update_marker_optimized(
                self.marker_index, start_frame, end_frame
            )

    def seek_to_frame(self, frame: int):
        """Seek playback to specific frame."""
        self.playback_controller.seek_to_frame(frame)
        self._update_current_frame()
        self.playback_position_changed.emit(frame)

    # Nudge operations with optimized updates
    def nudge_in_point(self, frames: int):
        """Nudge IN point by specified frames with optimized update."""
        if not self.marker:
            return

        new_start = max(0, self.marker.start_frame + frames)
        if new_start < self.marker.end_frame:
            self.marker.start_frame = new_start
            self.seek_to_frame(new_start)
            self.marker_updated.emit()

            # Оптимизированное обновление таймлайна
            if self.marker_index >= 0 and self.timeline_controller:
                self.timeline_controller.update_marker_optimized(
                    self.marker_index, new_start, self.marker.end_frame
                )

    def nudge_out_point(self, frames: int):
        """Nudge OUT point by specified frames with optimized update."""
        if not self.marker:
            return

        total_frames = self.get_total_frames()
        new_end = min(total_frames, self.marker.end_frame + frames)
        if new_end > self.marker.start_frame:
            self.marker.end_frame = new_end
            self.seek_to_frame(new_end)
            self.marker_updated.emit()

            # Оптимизированное обновление таймлайна
            if self.marker_index >= 0 and self.timeline_controller:
                self.timeline_controller.update_marker_optimized(
                    self.marker_index, self.marker.start_frame, new_end
                )

    # Point setting operations with optimized updates
    def set_in_point(self):
        """Set IN point to current playback position with optimized update."""
        if not self.marker:
            return

        current_frame = self.playback_controller.current_frame
        if current_frame < self.marker.end_frame:
            self.marker.start_frame = current_frame
            self.marker_updated.emit()

            # Оптимизированное обновление таймлайна
            if self.marker_index >= 0 and self.timeline_controller:
                self.timeline_controller.update_marker_optimized(
                    self.marker_index, current_frame, self.marker.end_frame
                )

    def set_out_point(self):
        """Set OUT point to current playback position with optimized update."""
        if not self.marker:
            return

        current_frame = self.playback_controller.current_frame
        if current_frame > self.marker.start_frame:
            self.marker.end_frame = current_frame
            self.marker_updated.emit()

            # Оптимизированное обновление таймлайна
            if self.marker_index >= 0 and self.timeline_controller:
                self.timeline_controller.update_marker_optimized(
                    self.marker_index, self.marker.start_frame, current_frame
                )

    # Active point management
    def set_active_point(self, point: str):
        """Set active editing point ('in' or 'out')."""
        if point in ['in', 'out']:
            self.active_point = point
            self.active_point_changed.emit(point)

            # Seek to active point
            frame = self.marker.start_frame if point == 'in' else self.marker.end_frame
            self.seek_to_frame(frame)

    def toggle_active_point(self):
        """Toggle between IN and OUT points."""
        new_point = 'out' if self.active_point == 'in' else 'in'
        self.set_active_point(new_point)

    def step_active_point(self, frames: int):
        """Step active point by specified frames."""
        if self.active_point == 'in':
            self.nudge_in_point(frames)
        else:
            self.nudge_out_point(frames)

    # Playback operations
    def toggle_playback(self):
        """Toggle play/pause."""
        if self.is_playing:
            self._pause_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        """Start loop playback."""
        if not self.marker:
            return

        self.is_playing = True

        # If we're at or past the end, restart from beginning
        current_frame = self.playback_controller.current_frame
        if current_frame >= self.marker.end_frame or current_frame < self.marker.start_frame:
            self.seek_to_frame(self.marker.start_frame)

        # Start timer
        fps = self.get_fps()
        if fps > 0:
            interval = int(1000 / fps)
            self.playback_timer.start(interval)

    def _pause_playback(self):
        """Pause playback."""
        self.is_playing = False
        self.playback_timer.stop()

    def _on_playback_tick(self):
        """Handle playback timer tick."""
        if not self.is_playing or not self.marker:
            return

        # Advance frame
        current_frame = self.playback_controller.current_frame + 1

        # Handle loop logic
        if self.loop_enabled:
            if current_frame >= self.marker.end_frame:
                current_frame = self.marker.start_frame

        # Seek to new frame
        self.seek_to_frame(current_frame)

        # Stop if we've reached the end and loop is disabled
        if not self.loop_enabled and current_frame >= self.marker.end_frame:
            self._pause_playback()

    def set_loop_enabled(self, enabled: bool):
        """Enable/disable loop playback."""
        self.loop_enabled = enabled

    # Navigation operations
    def navigate_previous(self):
        """Navigate to previous marker in filtered list."""
        if not self.filtered_markers or self.current_marker_idx <= 0:
            return False

        self.marker_updated.emit()  # Save current changes

        prev_idx = self.current_marker_idx - 1
        original_idx, prev_marker = self.filtered_markers[prev_idx]

        self.set_marker(prev_marker, original_idx, self.filtered_markers, prev_idx)
        return True

    def navigate_next(self):
        """Navigate to next marker in filtered list."""
        if not self.filtered_markers or self.current_marker_idx >= len(self.filtered_markers) - 1:
            return False

        self.marker_updated.emit()  # Save current changes

        next_idx = self.current_marker_idx + 1
        original_idx, next_marker = self.filtered_markers[next_idx]

        self.set_marker(next_marker, original_idx, self.filtered_markers, next_idx)
        return True

    # Data operations with optimized updates
    def update_event_type(self, event_name: str):
        """Update marker event type with optimized timeline update."""
        if self.marker:
            self.marker.event_name = event_name
            self.marker_updated.emit()

            # Оптимизированное обновление таймлайна
            if self.marker_index >= 0 and self.timeline_controller:
                self.timeline_controller.update_marker_optimized(
                    self.marker_index, self.marker.start_frame, self.marker.end_frame, event_name
                )

    def update_note(self, note: str):
        """Update marker note."""
        if self.marker:
            self.marker.note = note
            self.marker_updated.emit()

    def save_changes(self):
        """Save current marker changes."""
        self.marker_updated.emit()
        self.marker_saved.emit()

        # Navigate to next marker if available
        if not self.navigate_next():
            # No more markers, caller should close window
            pass

    # Video display operations
    def get_current_frame_pixmap(self) -> Optional[QPixmap]:
        """Get current frame as pixmap."""
        return self.current_frame_pixmap

    def _update_current_frame(self):
        """Update current frame display."""
        frame = self.video_service.get_current_frame()
        if frame is not None:
            # Convert to pixmap (implementation depends on video service)
            # For now, just emit signal that frame changed
            self.playback_position_changed.emit(self.playback_controller.current_frame)

    # Utility methods
    def get_time_string(self, frame: int) -> str:
        """Get formatted time string for frame."""
        fps = self.get_fps()
        return frames_to_time(frame, fps)

    def get_marker_time_strings(self) -> Tuple[str, str]:
        """Get formatted time strings for marker start/end."""
        if not self.marker:
            return "00:00", "00:00"

        return (
            self.get_time_string(self.marker.start_frame),
            self.get_time_string(self.marker.end_frame)
        )

    def get_available_event_types(self) -> List[str]:
        """Get available event types for combo box."""
        event_manager = get_custom_event_manager()
        return [event.get_localized_name() for event in event_manager.get_all_events()]

    def get_event_type_data(self, display_name: str) -> Optional[str]:
        """Get event name from display name."""
        event_manager = get_custom_event_manager()
        for event in event_manager.get_all_events():
            if event.get_localized_name() == display_name:
                return event.name
        return None

    def cleanup(self):
        """Cleanup resources."""
        self._pause_playback()
        self.marker = None
        self.marker_index = -1
        self.filtered_markers.clear()