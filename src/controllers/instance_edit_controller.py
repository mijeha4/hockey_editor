"""
Instance Edit Controller - manages segment editing operations.

Handles precise segment editing with visual timeline, loop playback,
hotkeys, and professional NLE-style controls for individual video segments.
"""

from __future__ import annotations

from typing import Optional, List, Tuple

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QPixmap

from models.domain.marker import Marker
from utils.time_utils import frames_to_time
from services.events.custom_event_manager import get_custom_event_manager, CustomEventManager


class InstanceEditController(QObject):
    """Controller for managing instance (segment) editing operations.

    Contract recommendation:
        start_frame is inclusive
        end_frame is exclusive  (segment covers frames [start_frame, end_frame))
    """

    # Signals
    marker_updated = Signal()                # Marker data changed (dirty)
    request_save_marker = Signal()           # Explicit "save now" request (optional)
    marker_saved = Signal()                  # Marker saved successfully

    playback_position_changed = Signal(int)  # Current frame changed
    timeline_range_changed = Signal(int, int)  # Start/end frames changed
    active_point_changed = Signal(str)       # 'in' or 'out'

    # Optional: expose pixmap if you want controller to provide it
    pixmap_changed = Signal(QPixmap)

    def __init__(self, main_controller, parent=None):
        super().__init__(parent)

        self.main_controller = main_controller
        self.playback_controller = main_controller.playback_controller
        self.video_service = main_controller.video_service

        self.event_manager: CustomEventManager = get_custom_event_manager()

        # Current marker being edited
        self.marker: Optional[Marker] = None

        # Navigation state: list of (original_index, marker)
        self.filtered_markers: List[Tuple[int, Marker]] = []
        self.current_marker_idx: int = 0

        # Playback state
        self.is_playing: bool = False
        self.loop_enabled: bool = True
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._on_playback_tick)

        # Editing state
        self.active_point: str = "in"  # 'in' or 'out'

        # If PlaybackController emits pixmap, you can forward it
        if hasattr(self.playback_controller, "pixmap_changed"):
            self.playback_controller.pixmap_changed.connect(self._on_pixmap_changed)

    # ─── Marker lifecycle ───

    def set_marker(
        self,
        marker: Marker,
        filtered_markers: Optional[List[Tuple[int, Marker]]] = None,
        current_idx: int = 0
    ) -> None:
        """Set the marker to edit."""
        self.marker = marker
        self.filtered_markers = filtered_markers or []
        self.current_marker_idx = current_idx

        # Seek to marker start
        self.seek_to_frame(marker.start_frame)
        self.timeline_range_changed.emit(marker.start_frame, marker.end_frame)

    def get_marker(self) -> Optional[Marker]:
        """Get the current marker (live object)."""
        return self.marker

    # ─── Video info ───

    def get_fps(self) -> float:
        return self.video_service.get_fps() if getattr(self.video_service, "cap", None) else 30.0

    def get_total_frames(self) -> int:
        return self.video_service.get_total_frames()

    # ─── Timeline operations ───

    def set_timeline_range(self, start_frame: int, end_frame: int) -> None:
        """Update marker range from timeline drag."""
        if not self.marker:
            return

        total_frames = self.get_total_frames()

        # Clamp: start in [0, total_frames-1]
        start_frame = max(0, min(start_frame, max(0, total_frames - 1)))

        # Clamp: end in [start+1, total_frames] (exclusive end allowed = total_frames)
        end_frame = max(start_frame + 1, min(end_frame, total_frames))

        if (start_frame, end_frame) == (self.marker.start_frame, self.marker.end_frame):
            return

        self.marker.start_frame = start_frame
        self.marker.end_frame = end_frame

        self.timeline_range_changed.emit(start_frame, end_frame)
        self.marker_updated.emit()

    def seek_to_frame(self, frame: int) -> None:
        """Seek playback to specific frame."""
        self.playback_controller.seek_to_frame(frame)
        self._update_current_frame()
        self.playback_position_changed.emit(frame)

    # ─── Nudge operations ───

    def nudge_in_point(self, frames: int) -> None:
        if not self.marker:
            return

        new_start = max(0, self.marker.start_frame + frames)
        if new_start < self.marker.end_frame:
            self.marker.start_frame = new_start
            self.seek_to_frame(new_start)
            self.timeline_range_changed.emit(self.marker.start_frame, self.marker.end_frame)
            self.marker_updated.emit()

    def nudge_out_point(self, frames: int) -> None:
        if not self.marker:
            return

        total_frames = self.get_total_frames()
        new_end = min(total_frames, self.marker.end_frame + frames)
        if new_end > self.marker.start_frame:
            self.marker.end_frame = new_end
            # Seek to last visible frame in the segment (end is exclusive)
            self.seek_to_frame(max(self.marker.start_frame, new_end - 1))
            self.timeline_range_changed.emit(self.marker.start_frame, self.marker.end_frame)
            self.marker_updated.emit()

    # ─── Point setting operations ───

    def set_in_point(self) -> None:
        if not self.marker:
            return

        current_frame = self.playback_controller.current_frame
        if current_frame < self.marker.end_frame:
            self.marker.start_frame = current_frame
            self.timeline_range_changed.emit(self.marker.start_frame, self.marker.end_frame)
            self.marker_updated.emit()

    def set_out_point(self) -> None:
        """Set OUT point to current playback position (exclusive end)."""
        if not self.marker:
            return

        current_frame = self.playback_controller.current_frame

        # If OUT is set on current frame, make end exclusive => current_frame + 1
        new_end = current_frame + 1
        total_frames = self.get_total_frames()
        new_end = min(total_frames, new_end)

        if new_end > self.marker.start_frame:
            self.marker.end_frame = new_end
            self.timeline_range_changed.emit(self.marker.start_frame, self.marker.end_frame)
            self.marker_updated.emit()

    # ─── Active point management ───

    def set_active_point(self, point: str) -> None:
        if point not in ("in", "out"):
            return
        if not self.marker:
            return

        self.active_point = point
        self.active_point_changed.emit(point)

        frame = self.marker.start_frame if point == "in" else max(self.marker.start_frame, self.marker.end_frame - 1)
        self.seek_to_frame(frame)

    def toggle_active_point(self) -> None:
        self.set_active_point("out" if self.active_point == "in" else "in")

    def step_active_point(self, frames: int) -> None:
        if self.active_point == "in":
            self.nudge_in_point(frames)
        else:
            self.nudge_out_point(frames)

    # ─── Playback operations ───

    def toggle_playback(self) -> None:
        if self.is_playing:
            self._pause_playback()
        else:
            self._start_playback()

    def _start_playback(self) -> None:
        if not self.marker:
            return

        self.is_playing = True

        current_frame = self.playback_controller.current_frame
        last_frame = max(self.marker.start_frame, self.marker.end_frame - 1)

        if current_frame > last_frame or current_frame < self.marker.start_frame:
            self.seek_to_frame(self.marker.start_frame)

        fps = self.get_fps()
        if fps > 0:
            interval_ms = max(1, round(1000 / fps))
            self.playback_timer.start(interval_ms)

    def _pause_playback(self) -> None:
        self.is_playing = False
        self.playback_timer.stop()

    def _on_playback_tick(self) -> None:
        if not self.is_playing or not self.marker:
            return

        current_frame = self.playback_controller.current_frame + 1
        last_frame = max(self.marker.start_frame, self.marker.end_frame - 1)

        if self.loop_enabled and current_frame > last_frame:
            current_frame = self.marker.start_frame

        self.seek_to_frame(current_frame)

        if not self.loop_enabled and current_frame >= last_frame:
            self._pause_playback()

    def set_loop_enabled(self, enabled: bool) -> None:
        self.loop_enabled = enabled

    # ─── Navigation operations ───

    def navigate_previous(self) -> bool:
        if not self.filtered_markers or self.current_marker_idx <= 0:
            return False

        self.request_save_marker.emit()

        prev_idx = self.current_marker_idx - 1
        _, prev_marker = self.filtered_markers[prev_idx]
        self.set_marker(prev_marker, self.filtered_markers, prev_idx)
        return True

    def navigate_next(self) -> bool:
        if not self.filtered_markers or self.current_marker_idx >= len(self.filtered_markers) - 1:
            return False

        self.request_save_marker.emit()

        next_idx = self.current_marker_idx + 1
        _, next_marker = self.filtered_markers[next_idx]
        self.set_marker(next_marker, self.filtered_markers, next_idx)
        return True

    # ─── Data operations ───

    def update_event_type(self, event_name: str) -> None:
        if not self.marker:
            return
        if self.marker.event_name != event_name:
            self.marker.event_name = event_name
            self.marker_updated.emit()

    def update_note(self, note: str) -> None:
        if not self.marker:
            return
        if self.marker.note != note:
            self.marker.note = note
            self.marker_updated.emit()

    def save_changes(self) -> None:
        """Request save of current marker and optionally auto-advance."""
        self.request_save_marker.emit()
        self.marker_saved.emit()

        self.navigate_next()  # if cannot, just stay

    # ─── Video display operations ───

    def _on_pixmap_changed(self, pixmap: QPixmap) -> None:
        self.pixmap_changed.emit(pixmap)

    def _update_current_frame(self) -> None:
        # We don't decode frames here; PlaybackController is responsible.
        self.playback_position_changed.emit(self.playback_controller.current_frame)

    # ─── Utility ───

    def get_time_string(self, frame: int) -> str:
        return frames_to_time(frame, self.get_fps())

    def get_marker_time_strings(self) -> Tuple[str, str]:
        if not self.marker:
            return "00:00", "00:00"
        return (
            self.get_time_string(self.marker.start_frame),
            self.get_time_string(self.marker.end_frame),
        )

    def get_event_type_items(self) -> List[Tuple[str, str]]:
        """Return list of (display_text, data_event_name)."""
        return [(e.get_localized_name(), e.name) for e in self.event_manager.get_all_events()]

    # ─── Cleanup ───

    def cleanup(self) -> None:
        self._pause_playback()
        self.marker = None
        self.filtered_markers.clear()