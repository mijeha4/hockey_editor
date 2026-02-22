"""
Preview Controller - manages the preview window functionality.

Handles playlist playback, segment filtering, drawing tools, and preview-specific
operations for reviewing video segments.
"""

from __future__ import annotations

from typing import Optional, List, Set, Tuple

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QColor

from models.domain.marker import Marker
from services.events.custom_event_manager import get_custom_event_manager


class PreviewController(QObject):
    """Controller for managing preview window operations.

    Contract assumption (recommended):
        Marker.start_frame is inclusive
        Marker.end_frame is exclusive
    """

    # Signals
    playback_position_changed = Signal(int)   # frame_idx
    active_segment_changed = Signal(int)      # marker_idx (original index in project.markers)
    filters_changed = Signal()

    drawing_tool_changed = Signal(str)
    drawing_color_changed = Signal(QColor)
    drawing_thickness_changed = Signal(int)

    def __init__(self, main_controller, parent=None):
        super().__init__(parent)

        self.main_controller = main_controller
        self.video_controller = main_controller.playback_controller

        # Playlist playback state
        self.current_marker_idx: int = 0  # original index in project.markers
        self.is_playing: bool = False

        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._on_playback_tick)

        # Filter state (локально для preview; можно заменить на общий FilterController)
        self.filter_event_types: Set[str] = set()
        self.filter_has_notes: bool = False
        self.filter_notes_search: str = ""

        # Drawing state
        self.drawing_tool = "cursor"
        self.drawing_color = QColor("#FF0000")
        self.drawing_thickness = 2

        # Optional: sync preview with main playback (if you want)
        # PlaybackController имеет frame_changed(int)
        self.video_controller.frame_changed.connect(self._on_main_frame_changed)

    # ─────────────────────────────────────────────────────────────────────────────
    # Segment selection / navigation
    # ─────────────────────────────────────────────────────────────────────────────

    def set_current_segment(self, marker_idx: int) -> None:
        """Set the currently active segment by original marker index."""
        markers = self.main_controller.project.markers
        if 0 <= marker_idx < len(markers):
            self.current_marker_idx = marker_idx
            marker = markers[marker_idx]

            # Jump to segment start
            self.video_controller.seek_to_frame_immediate(marker.start_frame)
            self.active_segment_changed.emit(marker_idx)

    def next_segment(self) -> bool:
        """Go to next filtered segment. Returns True if moved."""
        filtered_markers = self._get_filtered_markers()
        if not filtered_markers:
            return False

        # Find current segment in filtered list
        current_pos = -1
        for i, (orig_idx, _) in enumerate(filtered_markers):
            if orig_idx == self.current_marker_idx:
                current_pos = i
                break

        # If current segment is not in filtered list, jump to first
        if current_pos == -1:
            self.set_current_segment(filtered_markers[0][0])
            return True

        if current_pos < len(filtered_markers) - 1:
            next_orig_idx, _ = filtered_markers[current_pos + 1]
            self.set_current_segment(next_orig_idx)
            return True

        return False

    def previous_segment(self) -> bool:
        """Go to previous filtered segment. Returns True if moved."""
        filtered_markers = self._get_filtered_markers()
        if not filtered_markers:
            return False

        current_pos = -1
        for i, (orig_idx, _) in enumerate(filtered_markers):
            if orig_idx == self.current_marker_idx:
                current_pos = i
                break

        if current_pos == -1:
            self.set_current_segment(filtered_markers[0][0])
            return True

        if current_pos > 0:
            prev_orig_idx, _ = filtered_markers[current_pos - 1]
            self.set_current_segment(prev_orig_idx)
            return True

        return False

    # ─────────────────────────────────────────────────────────────────────────────
    # Playlist playback
    # ─────────────────────────────────────────────────────────────────────────────

    def start_playlist_playback(self) -> None:
        """Start playlist playback from current segment."""
        if not self._get_filtered_markers():
            return

        self.is_playing = True

        fps = self.main_controller.get_fps()
        speed = self.video_controller.get_speed() if hasattr(self.video_controller, "get_speed") else 1.0

        interval_ms = int(1000 / (fps * speed)) if fps > 0 else 33
        self.playback_timer.start(max(1, interval_ms))

    def pause_playlist_playback(self) -> None:
        self.is_playing = False
        self.playback_timer.stop()

    def stop_playlist_playback(self) -> None:
        self.pause_playlist_playback()
        # Reset to beginning of current segment
        markers = self.main_controller.project.markers
        if 0 <= self.current_marker_idx < len(markers):
            self.video_controller.seek_to_frame_immediate(markers[self.current_marker_idx].start_frame)

    def _on_playback_tick(self) -> None:
        """One tick of preview playlist playback."""
        if not self.is_playing:
            return

        markers = self.main_controller.project.markers
        if not (0 <= self.current_marker_idx < len(markers)):
            self.stop_playlist_playback()
            return

        marker = markers[self.current_marker_idx]

        current_frame = self.video_controller.current_frame

        # If reached segment end -> go next segment or stop
        if current_frame >= marker.end_frame:
            moved = self.next_segment()
            if not moved:
                self.stop_playlist_playback()
            return

        # Advance by 1 frame (immediate display)
        self.video_controller.seek_to_frame_immediate(current_frame + 1)
        self.playback_position_changed.emit(self.video_controller.current_frame)

    # ─────────────────────────────────────────────────────────────────────────────
    # Sync from main playback (optional)
    # ─────────────────────────────────────────────────────────────────────────────

    def _on_main_frame_changed(self, frame_idx: int) -> None:
        """Follow main playback head changes (if preview window listens)."""
        self.playback_position_changed.emit(frame_idx)

        # Update active segment based on current frame
        for idx, marker in enumerate(self.main_controller.project.markers):
            # Using end as exclusive:
            if marker.start_frame <= frame_idx < marker.end_frame:
                if idx != self.current_marker_idx:
                    self.current_marker_idx = idx
                    self.active_segment_changed.emit(idx)
                break

    # ─────────────────────────────────────────────────────────────────────────────
    # Filter management
    # ─────────────────────────────────────────────────────────────────────────────

    def set_event_type_filter(self, event_types: Set[str]) -> None:
        self.filter_event_types = event_types.copy()
        self.filters_changed.emit()

    def set_notes_filter(self, has_notes: bool) -> None:
        self.filter_has_notes = has_notes
        self.filters_changed.emit()

    def set_notes_search_filter(self, search_text: str) -> None:
        self.filter_notes_search = (search_text or "").lower().strip()
        self.filters_changed.emit()

    def reset_filters(self) -> None:
        self.filter_event_types.clear()
        self.filter_has_notes = False
        self.filter_notes_search = ""
        self.filters_changed.emit()

    def _get_filtered_markers(self) -> List[Tuple[int, Marker]]:
        """Get filtered markers with their original indices."""
        return [
            (idx, marker)
            for idx, marker in enumerate(self.main_controller.project.markers)
            if self._passes_filters(marker)
        ]

    def _passes_filters(self, marker: Marker) -> bool:
        if self.filter_event_types and marker.event_name not in self.filter_event_types:
            return False

        note = (marker.note or "")
        if self.filter_has_notes and not note.strip():
            return False

        if self.filter_notes_search and self.filter_notes_search not in note.lower():
            return False

        return True

    def get_available_event_types(self) -> List[str]:
        event_manager = get_custom_event_manager()
        return [event.name for event in event_manager.get_all_events()]

    # ─────────────────────────────────────────────────────────────────────────────
    # Drawing tools management
    # ─────────────────────────────────────────────────────────────────────────────

    def set_drawing_tool(self, tool: str) -> None:
        valid_tools = ["cursor", "line", "rectangle", "circle", "arrow"]
        if tool in valid_tools and tool != self.drawing_tool:
            self.drawing_tool = tool
            self.drawing_tool_changed.emit(tool)

    def set_drawing_color(self, color: QColor) -> None:
        if color != self.drawing_color:
            self.drawing_color = color
            self.drawing_color_changed.emit(color)

    def set_drawing_thickness(self, thickness: int) -> None:
        thickness = max(1, min(10, int(thickness)))
        if thickness != self.drawing_thickness:
            self.drawing_thickness = thickness
            self.drawing_thickness_changed.emit(self.drawing_thickness)

    def get_drawing_tool(self) -> str:
        return self.drawing_tool

    def get_drawing_color(self) -> QColor:
        return self.drawing_color

    def get_drawing_thickness(self) -> int:
        return self.drawing_thickness

    # ─────────────────────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────────────────────

    def get_current_segment_time_info(self) -> tuple[str, str]:
        """Get current segment time info (current_time / total_time)."""
        markers = self.main_controller.project.markers
        if not (0 <= self.current_marker_idx < len(markers)):
            return "00:00", "00:00"

        marker = markers[self.current_marker_idx]
        fps = self.main_controller.get_fps()
        if fps <= 0:
            return "00:00", "00:00"

        current_frame = self.video_controller.current_frame
        current_time = (current_frame - marker.start_frame) / fps
        total_time = (marker.end_frame - marker.start_frame) / fps

        def format_time(seconds: float) -> str:
            seconds = max(0.0, seconds)
            minutes = int(seconds) // 60
            secs = int(seconds) % 60
            return f"{minutes:02d}:{secs:02d}"

        return format_time(current_time), format_time(total_time)

    def seek_in_segment(self, position: float) -> None:
        """Seek to position within current segment (0.0 to 1.0)."""
        markers = self.main_controller.project.markers
        if not (0 <= self.current_marker_idx < len(markers)):
            return

        marker = markers[self.current_marker_idx]
        position = max(0.0, min(1.0, float(position)))

        frame_range = max(1, marker.end_frame - marker.start_frame)
        target_frame = marker.start_frame + int(frame_range * position)

        # Clamp to [start, end-1]
        target_frame = min(max(marker.start_frame, target_frame), max(marker.start_frame, marker.end_frame - 1))
        self.video_controller.seek_to_frame_immediate(target_frame)

    def cleanup(self) -> None:
        self.playback_timer.stop()
        self.is_playing = False
        try:
            self.video_controller.frame_changed.disconnect(self._on_main_frame_changed)
        except Exception:
            pass