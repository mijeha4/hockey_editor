"""
Preview Controller - manages the preview window functionality.

Handles playlist playback, segment filtering, drawing tools, and preview-specific
operations for reviewing video segments.
"""

from typing import Optional, List, Set
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QColor

# Импорты для работы из корня проекта (main.py добавляет src в sys.path)
from models.domain.marker import Marker
from hockey_editor.utils.custom_events import get_custom_event_manager


class PreviewController(QObject):
    """Controller for managing preview window operations."""

    # Signals
    playback_position_changed = Signal(int)  # frame_idx
    active_segment_changed = Signal(int)    # marker_idx
    filters_changed = Signal()              # filters updated
    drawing_tool_changed = Signal(str)      # tool_name
    drawing_color_changed = Signal(QColor)  # color
    drawing_thickness_changed = Signal(int) # thickness

    def __init__(self, main_controller, parent=None):
        super().__init__(parent)

        self.main_controller = main_controller
        self.video_controller = main_controller.playback_controller

        # Playback state
        self.current_marker_idx = 0
        self.is_playing = False
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)

        # Filter state
        self.filter_event_types: Set[str] = set()
        self.filter_has_notes: bool = False
        self.filter_notes_search: str = ""

        # Drawing state
        self.drawing_tool = "cursor"  # cursor, line, rectangle, circle, arrow
        self.drawing_color = QColor("#FF0000")
        self.drawing_thickness = 2

        # Connect to main controller signals
        # Note: PlaybackController may not have playback_time_changed signal
        # We can connect to video_controller directly if needed
        pass

    def set_current_segment(self, marker_idx: int):
        """Set the currently active segment."""
        if 0 <= marker_idx < len(self.main_controller.project.markers):
            self.current_marker_idx = marker_idx
            marker = self.main_controller.project.markers[marker_idx]
            self.video_controller.seek_frame(marker.start_frame)
            self.active_segment_changed.emit(marker_idx)

    def start_playlist_playback(self):
        """Start playlist playback from current segment."""
        if not self._get_filtered_markers():
            return

        self.is_playing = True
        fps = self.video_controller.get_fps()
        speed = self.video_controller.get_playback_speed()
        if fps > 0:
            self.playback_timer.setInterval(int(1000 / (fps * speed)))
        self.playback_timer.start()

    def pause_playlist_playback(self):
        """Pause playlist playback."""
        self.is_playing = False
        self.playback_timer.stop()

    def stop_playlist_playback(self):
        """Stop playlist playback."""
        self.pause_playlist_playback()
        # Reset to beginning of current segment
        if self.current_marker_idx < len(self.main_controller.project.markers):
            marker = self.main_controller.project.markers[self.current_marker_idx]
            self.video_controller.seek_frame(marker.start_frame)

    def next_segment(self):
        """Go to next filtered segment."""
        filtered_markers = self._get_filtered_markers()
        if not filtered_markers:
            return

        # Find current segment in filtered list
        current_original_idx = None
        current_filtered_idx = -1

        for i, (orig_idx, marker) in enumerate(filtered_markers):
            if orig_idx == self.current_marker_idx:
                current_original_idx = orig_idx
                current_filtered_idx = i
                break

        if current_filtered_idx >= 0 and current_filtered_idx < len(filtered_markers) - 1:
            next_orig_idx, next_marker = filtered_markers[current_filtered_idx + 1]
            self.set_current_segment(next_orig_idx)

    def previous_segment(self):
        """Go to previous filtered segment."""
        filtered_markers = self._get_filtered_markers()
        if not filtered_markers:
            return

        # Find current segment in filtered list
        current_filtered_idx = -1
        for i, (orig_idx, marker) in enumerate(filtered_markers):
            if orig_idx == self.current_marker_idx:
                current_filtered_idx = i
                break

        if current_filtered_idx > 0:
            prev_orig_idx, prev_marker = filtered_markers[current_filtered_idx - 1]
            self.set_current_segment(prev_orig_idx)

    def _on_playback_tick(self):
        """Handle playback timer tick."""
        if not self.is_playing:
            return

        current_frame = self.video_controller.get_current_frame_idx()
        current_marker = self.main_controller.project.markers[self.current_marker_idx]

        # Check if we've reached the end of current segment
        if current_frame >= current_marker.end_frame:
            # Try to go to next segment
            self.next_segment()

            # If we couldn't go to next segment, stop playback
            if self.current_marker_idx >= len(self.main_controller.project.markers) or \
               self.main_controller.project.markers[self.current_marker_idx] != current_marker:
                # We successfully moved to next segment, continue playback
                pass
            else:
                # No more segments, stop playback
                self.stop_playlist_playback()
                return

        # Continue playback
        self.video_controller.advance_frame()
        self.playback_position_changed.emit(self.video_controller.get_current_frame_idx())

    def _on_main_playback_time_changed(self, frame_idx: int):
        """Handle main playback time changes."""
        self.playback_position_changed.emit(frame_idx)

        # Update active segment based on current frame
        for idx, marker in enumerate(self.main_controller.project.markers):
            if marker.start_frame <= frame_idx <= marker.end_frame:
                if idx != self.current_marker_idx:
                    self.current_marker_idx = idx
                    self.active_segment_changed.emit(idx)
                break

    # Filter management
    def set_event_type_filter(self, event_types: Set[str]):
        """Set event type filter."""
        self.filter_event_types = event_types.copy()
        self.filters_changed.emit()

    def set_notes_filter(self, has_notes: bool):
        """Set notes filter."""
        self.filter_has_notes = has_notes
        self.filters_changed.emit()

    def set_notes_search_filter(self, search_text: str):
        """Set notes search filter."""
        self.filter_notes_search = search_text.lower().strip()
        self.filters_changed.emit()

    def reset_filters(self):
        """Reset all filters."""
        self.filter_event_types.clear()
        self.filter_has_notes = False
        self.filter_notes_search = ""
        self.filters_changed.emit()

    def _get_filtered_markers(self) -> List[tuple[int, Marker]]:
        """Get filtered markers with their original indices."""
        filtered = []
        for idx, marker in enumerate(self.main_controller.project.markers):
            if self._passes_filters(marker):
                filtered.append((idx, marker))
        return filtered

    def _passes_filters(self, marker: Marker) -> bool:
        """Check if marker passes current filters."""
        # Event type filter
        if self.filter_event_types and marker.event_name not in self.filter_event_types:
            return False

        # Notes filter
        if self.filter_has_notes and not marker.note.strip():
            return False

        # Notes search filter
        if self.filter_notes_search and self.filter_notes_search not in marker.note.lower():
            return False

        return True

    def get_available_event_types(self) -> List[str]:
        """Get available event types for filtering."""
        event_manager = get_custom_event_manager()
        return [event.name for event in event_manager.get_all_events()]

    # Drawing tools management
    def set_drawing_tool(self, tool: str):
        """Set active drawing tool."""
        valid_tools = ["cursor", "line", "rectangle", "circle", "arrow"]
        if tool in valid_tools:
            self.drawing_tool = tool
            self.drawing_tool_changed.emit(tool)

    def set_drawing_color(self, color: QColor):
        """Set drawing color."""
        self.drawing_color = color
        self.drawing_color_changed.emit(color)

    def set_drawing_thickness(self, thickness: int):
        """Set drawing thickness."""
        self.drawing_thickness = max(1, min(10, thickness))  # Clamp to reasonable range
        self.drawing_thickness_changed.emit(self.drawing_thickness)

    def get_drawing_tool(self) -> str:
        """Get current drawing tool."""
        return self.drawing_tool

    def get_drawing_color(self) -> QColor:
        """Get current drawing color."""
        return self.drawing_color

    def get_drawing_thickness(self) -> int:
        """Get current drawing thickness."""
        return self.drawing_thickness

    # Utility methods
    def get_current_segment_time_info(self) -> tuple[str, str]:
        """Get current segment time info (current_time / total_time)."""
        if self.current_marker_idx >= len(self.main_controller.project.markers):
            return "00:00", "00:00"

        marker = self.main_controller.project.markers[self.current_marker_idx]
        fps = self.video_controller.get_fps()

        if fps <= 0:
            return "00:00", "00:00"

        current_frame = self.video_controller.get_current_frame_idx()
        current_time = (current_frame - marker.start_frame) / fps
        total_time = (marker.end_frame - marker.start_frame) / fps

        def format_time(seconds: float) -> str:
            minutes = int(seconds) // 60
            secs = int(seconds) % 60
            return f"{minutes:02d}:{secs:02d}"

        return format_time(current_time), format_time(total_time)

    def seek_in_segment(self, position: float):
        """Seek to position within current segment (0.0 to 1.0)."""
        if self.current_marker_idx >= len(self.main_controller.project.markers):
            return

        marker = self.main_controller.project.markers[self.current_marker_idx]
        frame_range = marker.end_frame - marker.start_frame
        target_frame = marker.start_frame + int(frame_range * position)

        self.video_controller.seek_frame(target_frame)

    def cleanup(self):
        """Cleanup resources."""
        self.playback_timer.stop()
        self.is_playing = False
