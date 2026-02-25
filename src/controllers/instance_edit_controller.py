"""
Instance Edit Controller - manages segment editing operations.
CHANGED: добавлена поддержка undo/redo для сессии редактирования.
"""

from __future__ import annotations

import copy
from typing import Optional, List, Tuple

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QPixmap

from models.domain.marker import Marker
from utils.time_utils import frames_to_time
from services.events.custom_event_manager import get_custom_event_manager, CustomEventManager
from services.history.command_interface import Command
from services.history import get_history_manager


# ──────────────────────────────────────────────────────────────────────────────
# Команда для undo сессии редактирования
# ──────────────────────────────────────────────────────────────────────────────

class _InstanceEditCommand(Command):
    """Команда для undo/redo целой сессии редактирования маркера.

    Вся сессия (nudge in/out, смена типа, заметки) —
    одна атомарная операция с точки зрения undo.
    """

    def __init__(self, project, marker_idx: int,
                 old_marker: Marker, new_marker: Marker):
        event_name = new_marker.event_name or "маркер"
        super().__init__(f"Редактирование: {event_name}")
        self._project = project
        self._idx = marker_idx
        self._old = old_marker
        self._new = new_marker

    def execute(self) -> None:
        if 0 <= self._idx < len(self._project.markers):
            self._project.update_marker(self._idx, self._new)

    def undo(self) -> None:
        if 0 <= self._idx < len(self._project.markers):
            self._project.update_marker(self._idx, self._old)


# ──────────────────────────────────────────────────────────────────────────────

class InstanceEditController(QObject):
    """Controller for managing instance (segment) editing operations."""

    # Signals
    marker_updated = Signal()
    request_save_marker = Signal()
    marker_saved = Signal()

    playback_position_changed = Signal(int)
    timeline_range_changed = Signal(int, int)
    active_point_changed = Signal(str)

    pixmap_changed = Signal(QPixmap)

    def __init__(self, main_controller, parent=None):
        super().__init__(parent)

        self.main_controller = main_controller
        self.playback_controller = main_controller.playback_controller
        self.video_service = main_controller.video_service

        self.event_manager: CustomEventManager = get_custom_event_manager()

        self.marker: Optional[Marker] = None

        self.filtered_markers: List[Tuple[int, Marker]] = []
        self.current_marker_idx: int = 0

        self.is_playing: bool = False
        self.loop_enabled: bool = True
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._on_playback_tick)

        self.active_point: str = "in"

        self._edit_window = None

        # CHANGED: для undo-отслеживания сессии редактирования
        self._edit_original: Optional[Marker] = None

        if hasattr(self.playback_controller, "pixmap_changed"):
            self.playback_controller.pixmap_changed.connect(self._on_pixmap_changed)

    # ─── Open editor ───

    def open_editor(self, marker_idx: int) -> None:
        """Open the instance edit window for specific marker by original index."""
        markers = self.main_controller.project.markers
        if not (0 <= marker_idx < len(markers)):
            return

        marker = markers[marker_idx]

        all_pairs = [(i, m) for i, m in enumerate(markers)]

        current_filtered_idx = 0
        for i, (orig_idx, m) in enumerate(all_pairs):
            if orig_idx == marker_idx:
                current_filtered_idx = i
                break

        self.set_marker(marker, all_pairs, current_filtered_idx)

        try:
            from views.windows.instance_edit import InstanceEditWindow
            self._edit_window = InstanceEditWindow(
                marker, self.main_controller, all_pairs, current_filtered_idx, None
            )
            if hasattr(self._edit_window, 'marker_updated'):
                self._edit_window.marker_updated.connect(self._on_external_marker_update)
            self._edit_window.show()
        except Exception as e:
            print(f"ERROR: Failed to open instance edit window: {e}")
            import traceback
            traceback.print_exc()

    def _on_external_marker_update(self) -> None:
        self.marker_updated.emit()
        if hasattr(self.main_controller, 'timeline_controller'):
            self.main_controller.timeline_controller.refresh_view()

    # ─── Marker lifecycle ───

    def set_marker(
        self,
        marker: Marker,
        filtered_markers: Optional[List[Tuple[int, Marker]]] = None,
        current_idx: int = 0
    ) -> None:
        # CHANGED: зафиксировать предыдущую правку в истории
        self._commit_edit_to_history()

        self.marker = marker
        self.filtered_markers = filtered_markers or []
        self.current_marker_idx = current_idx

        # CHANGED: сохранить оригинальное состояние для undo
        self._edit_original = copy.deepcopy(marker)

        self.seek_to_frame(marker.start_frame)
        self.timeline_range_changed.emit(marker.start_frame, marker.end_frame)

    def get_marker(self) -> Optional[Marker]:
        return self.marker

    # ─── CHANGED: Undo-интеграция ───

    def _find_marker_index(self) -> int:
        """Найти текущий индекс редактируемого маркера в проекте."""
        if self.marker is None:
            return -1
        markers = self.main_controller.project.markers
        # Быстрая проверка по ссылке
        try:
            return markers.index(self.marker)
        except ValueError:
            pass
        # Fallback: по id
        for i, m in enumerate(markers):
            if m.id == self.marker.id:
                return i
        return -1

    def _has_marker_changed(self) -> bool:
        """Проверить, изменился ли маркер с начала сессии."""
        if self._edit_original is None or self.marker is None:
            return False
        return (
            self.marker.start_frame != self._edit_original.start_frame
            or self.marker.end_frame != self._edit_original.end_frame
            or self.marker.event_name != self._edit_original.event_name
            or self.marker.note != self._edit_original.note
        )

    def _commit_edit_to_history(self) -> None:
        """Зафиксировать текущую сессию редактирования в истории undo.

        Вызывается при:
          - навигации к другому маркеру (navigate_previous/next)
          - закрытии редактора (cleanup)
          - явном сохранении (save_changes)
        """
        if not self._has_marker_changed():
            self._edit_original = None
            return

        marker_idx = self._find_marker_index()
        if marker_idx < 0:
            self._edit_original = None
            return

        # Копия текущего (уже изменённого) состояния
        new_marker_copy = copy.deepcopy(self.marker)

        cmd = _InstanceEditCommand(
            self.main_controller.project,
            marker_idx,
            self._edit_original,      # состояние ДО редактирования
            new_marker_copy,           # состояние ПОСЛЕ
        )

        # push_done_command: добавить в стек БЕЗ вызова execute(),
        # т.к. изменение уже применено напрямую
        history = get_history_manager()
        history.push_command(cmd)

        self._edit_original = None

    # ─── Video info ───

    def get_fps(self) -> float:
        return self.video_service.get_fps() if getattr(self.video_service, "cap", None) else 30.0

    def get_total_frames(self) -> int:
        return self.video_service.get_total_frames()

    # ─── Timeline operations ───

    def set_timeline_range(self, start_frame: int, end_frame: int) -> None:
        if not self.marker:
            return
        total_frames = self.get_total_frames()
        start_frame = max(0, min(start_frame, max(0, total_frames - 1)))
        end_frame = max(start_frame + 1, min(end_frame, total_frames))
        if (start_frame, end_frame) == (self.marker.start_frame, self.marker.end_frame):
            return
        self.marker.start_frame = start_frame
        self.marker.end_frame = end_frame
        self.timeline_range_changed.emit(start_frame, end_frame)
        self.marker_updated.emit()

    def seek_to_frame(self, frame: int) -> None:
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
        if not self.marker:
            return
        current_frame = self.playback_controller.current_frame
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
        # CHANGED: commit перед навигацией
        self._commit_edit_to_history()
        self.request_save_marker.emit()
        prev_idx = self.current_marker_idx - 1
        _, prev_marker = self.filtered_markers[prev_idx]
        self.set_marker(prev_marker, self.filtered_markers, prev_idx)
        return True

    def navigate_next(self) -> bool:
        if not self.filtered_markers or self.current_marker_idx >= len(self.filtered_markers) - 1:
            return False
        # CHANGED: commit перед навигацией
        self._commit_edit_to_history()
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
        # CHANGED: commit перед сохранением
        self._commit_edit_to_history()
        self.request_save_marker.emit()
        self.marker_saved.emit()
        self.navigate_next()

    # ─── Video display operations ───

    def _on_pixmap_changed(self, pixmap: QPixmap) -> None:
        self.pixmap_changed.emit(pixmap)

    def _update_current_frame(self) -> None:
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
        return [(e.get_localized_name(), e.name) for e in self.event_manager.get_all_events()]

    # ─── Cleanup ───

    def cleanup(self) -> None:
        # CHANGED: commit при закрытии редактора
        self._commit_edit_to_history()
        self._pause_playback()
        if self._edit_window:
            try:
                self._edit_window.close()
            except Exception:
                pass
            self._edit_window = None
        self.marker = None
        self._edit_original = None
        self.filtered_markers.clear()