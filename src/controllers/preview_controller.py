"""
Preview Controller — управляет воспроизведением, навигацией,
фильтрацией и инструментами в окне предпросмотра.
"""

from __future__ import annotations

import os
import re
from typing import Optional, List, Set, Tuple, TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtGui import QColor, QPixmap

from models.domain.marker import Marker
from services.events.custom_event_manager import get_custom_event_manager

if TYPE_CHECKING:
    from views.widgets.drawing_overlay import DrawingOverlay


class PreviewController(QObject):
    """Контроллер окна предпросмотра."""

    # ── Signals ──
    playback_state_changed = Signal(bool)       # is_playing
    playback_position_changed = Signal(int)     # frame_idx
    active_segment_changed = Signal(int)        # marker_idx
    segment_counter_changed = Signal(str)       # "Goal (3 / 12)"
    loop_state_changed = Signal(bool)           # loop_enabled
    speed_changed = Signal(float)               # speed
    filters_changed = Signal()

    drawing_tool_changed = Signal(str)
    drawing_color_changed = Signal(QColor)
    drawing_thickness_changed = Signal(int)

    def __init__(self, main_controller, parent=None):
        super().__init__(parent)

        self.mc = main_controller
        self.pc = main_controller.playback_controller

        # ── Playback state ──
        self.current_marker_idx: int = 0
        self.is_playing: bool = False
        self.loop_enabled: bool = True
        self._speed: float = 1.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        # ── Filters ──
        self.filter_event_types: Set[str] = set()
        self.filter_has_notes: bool = False
        self.filter_notes_search: str = ""

        # ── Drawing ──
        self.drawing_tool: str = "cursor"
        self.drawing_color: QColor = QColor("#FF0000")
        self.drawing_thickness: int = 2

        # ── Sync with main playback ──
        self.pc.pixmap_changed.connect(self._on_pixmap_available)

    # ═══════════════════════════════════════════════════════════════════════
    #  Properties
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def markers(self) -> List[Marker]:
        return self.mc.project.markers

    @property
    def fps(self) -> float:
        return self.mc.get_fps()

    @property
    def current_frame(self) -> int:
        return self.pc.current_frame

    def get_current_marker(self) -> Optional[Marker]:
        if 0 <= self.current_marker_idx < len(self.markers):
            return self.markers[self.current_marker_idx]
        return None

    # ═══════════════════════════════════════════════════════════════════════
    #  Playback
    # ═══════════════════════════════════════════════════════════════════════

    def toggle_play_pause(self) -> None:
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        if not self.get_filtered_markers():
            return
        marker = self.get_current_marker()
        if not marker:
            return

        # Если текущий кадр вне сегмента — перемотать на начало
        if self.current_frame < marker.start_frame or self.current_frame >= marker.end_frame:
            self.pc.seek_to_frame_immediate(marker.start_frame)

        self.is_playing = True
        self._timer.start(self._calc_interval())
        self.playback_state_changed.emit(True)

    def pause(self) -> None:
        self.is_playing = False
        self._timer.stop()
        self.playback_state_changed.emit(False)

    def stop(self) -> None:
        self.pause()
        marker = self.get_current_marker()
        if marker:
            self.pc.seek_to_frame_immediate(marker.start_frame)
            self.playback_position_changed.emit(marker.start_frame)

    def step_frame(self, delta: int) -> None:
        """Покадровая навигация внутри текущего сегмента."""
        marker = self.get_current_marker()
        if not marker:
            return
        if self.is_playing:
            self.pause()

        new_frame = self.current_frame + delta
        new_frame = max(marker.start_frame, min(new_frame, marker.end_frame - 1))
        self.pc.seek_to_frame_immediate(new_frame)
        self.playback_position_changed.emit(new_frame)

    def seek_to_frame_in_segment(self, frame: int) -> None:
        """Перемотка к кадру (ограничено текущим сегментом)."""
        marker = self.get_current_marker()
        if not marker:
            return
        frame = max(marker.start_frame, min(frame, marker.end_frame - 1))
        self.pc.seek_to_frame_immediate(frame)
        self.playback_position_changed.emit(frame)

    # ── Speed ──

    def set_speed(self, speed: float) -> None:
        self._speed = max(0.1, speed)
        if self.is_playing:
            self._timer.start(self._calc_interval())
        self.speed_changed.emit(self._speed)

    def get_speed(self) -> float:
        return self._speed

    # ── Loop ──

    def toggle_loop(self) -> None:
        self.loop_enabled = not self.loop_enabled
        self.loop_state_changed.emit(self.loop_enabled)

    def set_loop_enabled(self, enabled: bool) -> None:
        self.loop_enabled = enabled
        self.loop_state_changed.emit(self.loop_enabled)

    # ── Timer ──

    def _calc_interval(self) -> int:
        fps = self.fps
        if fps <= 0:
            return 33
        return max(1, int(1000 / (fps * self._speed)))

    def _on_tick(self) -> None:
        if not self.is_playing:
            return

        marker = self.get_current_marker()
        if not marker:
            self.pause()
            return

        next_frame = self.current_frame + 1

        if next_frame >= marker.end_frame:
            if self.loop_enabled:
                # Повтор текущего сегмента
                self.pc.seek_to_frame_immediate(marker.start_frame)
                self.playback_position_changed.emit(marker.start_frame)
            else:
                # Переход к следующему или стоп
                if not self._auto_advance():
                    self.pause()
            return

        self.pc.seek_to_frame_immediate(next_frame)
        self.playback_position_changed.emit(next_frame)

    def _on_pixmap_available(self, pixmap: QPixmap, frame_idx: int) -> None:
        """Пробрасываем обновление pixmap наружу (для отображения)."""
        pass  # Window подписана на pc.pixmap_changed напрямую

    # ═══════════════════════════════════════════════════════════════════════
    #  Segment Navigation
    # ═══════════════════════════════════════════════════════════════════════

    def set_current_segment(self, marker_idx: int) -> None:
        """Перейти к сегменту по оригинальному индексу в project.markers."""
        if 0 <= marker_idx < len(self.markers):
            self.current_marker_idx = marker_idx
            marker = self.markers[marker_idx]
            self.pc.seek_to_frame_immediate(marker.start_frame)
            self.active_segment_changed.emit(marker_idx)
            self._emit_counter()
            self.playback_position_changed.emit(marker.start_frame)

    def next_segment(self) -> bool:
        """Перейти к следующему отфильтрованному сегменту."""
        filtered = self.get_filtered_markers()
        pos = self._find_current_pos(filtered)
        if pos < len(filtered) - 1:
            self.set_current_segment(filtered[pos + 1][0])
            return True
        return False

    def previous_segment(self) -> bool:
        """Перейти к предыдущему отфильтрованному сегменту."""
        filtered = self.get_filtered_markers()
        pos = self._find_current_pos(filtered)
        if pos > 0:
            self.set_current_segment(filtered[pos - 1][0])
            return True
        return False

    def _auto_advance(self) -> bool:
        """Автопереход к следующему сегменту при выключенном loop."""
        filtered = self.get_filtered_markers()
        pos = self._find_current_pos(filtered)
        if pos < len(filtered) - 1:
            next_idx = filtered[pos + 1][0]
            self.current_marker_idx = next_idx
            marker = self.markers[next_idx]
            self.pc.seek_to_frame_immediate(marker.start_frame)
            self.active_segment_changed.emit(next_idx)
            self._emit_counter()
            self.playback_position_changed.emit(marker.start_frame)
            return True
        return False

    def _find_current_pos(self, filtered: List[Tuple[int, Marker]]) -> int:
        """Найти позицию текущего сегмента в отфильтрованном списке."""
        for i, (orig_idx, _) in enumerate(filtered):
            if orig_idx == self.current_marker_idx:
                return i
        return 0 if filtered else -1

    def has_next(self) -> bool:
        filtered = self.get_filtered_markers()
        pos = self._find_current_pos(filtered)
        return pos < len(filtered) - 1

    def has_prev(self) -> bool:
        filtered = self.get_filtered_markers()
        pos = self._find_current_pos(filtered)
        return pos > 0

    # ═══════════════════════════════════════════════════════════════════════
    #  Counter
    # ═══════════════════════════════════════════════════════════════════════

    def get_counter_text(self) -> str:
        filtered = self.get_filtered_markers()
        if not filtered:
            return "0 / 0"
        pos = self._find_current_pos(filtered)
        marker = self.get_current_marker()
        name = marker.event_name if marker else ""

        # Попробовать локализованное имя
        try:
            em = get_custom_event_manager()
            ev = em.get_event(name)
            if ev:
                name = ev.get_localized_name()
        except Exception:
            pass

        return f"{name} ({pos + 1} / {len(filtered)})"

    def _emit_counter(self) -> None:
        self.segment_counter_changed.emit(self.get_counter_text())

    # ═══════════════════════════════════════════════════════════════════════
    #  Time Info
    # ═══════════════════════════════════════════════════════════════════════

    def get_time_text(self) -> str:
        marker = self.get_current_marker()
        if not marker or self.fps <= 0:
            return "00:00 / 00:00"
        current = self.current_frame / self.fps
        end = marker.end_frame / self.fps
        return f"{self._fmt(current)} / {self._fmt(end)}"

    def get_slider_range(self) -> Tuple[int, int, int]:
        """Вернуть (min, max, current) для слайдера."""
        marker = self.get_current_marker()
        if not marker:
            return (0, 0, 0)
        return (marker.start_frame, marker.end_frame, self.current_frame)

    @staticmethod
    def _fmt(seconds: float) -> str:
        s = max(0.0, seconds)
        return f"{int(s) // 60:02d}:{int(s) % 60:02d}"

    # ═══════════════════════════════════════════════════════════════════════
    #  Filters
    # ═══════════════════════════════════════════════════════════════════════

    def set_event_type_filter(self, event_types: Set[str]) -> None:
        self.filter_event_types = event_types.copy()
        self.filters_changed.emit()
        self._emit_counter()

    def set_notes_filter(self, has_notes: bool) -> None:
        self.filter_has_notes = has_notes
        self.filters_changed.emit()
        self._emit_counter()

    def set_notes_search(self, text: str) -> None:
        self.filter_notes_search = (text or "").lower().strip()
        self.filters_changed.emit()
        self._emit_counter()

    def reset_filters(self) -> None:
        self.filter_event_types.clear()
        self.filter_has_notes = False
        self.filter_notes_search = ""
        self.filters_changed.emit()
        self._emit_counter()

    def get_filtered_markers(self) -> List[Tuple[int, Marker]]:
        return [
            (idx, m) for idx, m in enumerate(self.markers)
            if self._passes(m)
        ]

    def _passes(self, marker: Marker) -> bool:
        if self.filter_event_types and marker.event_name not in self.filter_event_types:
            return False
        if self.filter_has_notes and not (marker.note or "").strip():
            return False
        if self.filter_notes_search and self.filter_notes_search not in (marker.note or "").lower():
            return False
        return True

    # ═══════════════════════════════════════════════════════════════════════
    #  Drawing tools
    # ═══════════════════════════════════════════════════════════════════════

    def set_drawing_tool(self, tool: str) -> None:
        self.drawing_tool = tool
        self.drawing_tool_changed.emit(tool)

    def set_drawing_color(self, color: QColor) -> None:
        self.drawing_color = color
        self.drawing_color_changed.emit(color)

    def set_drawing_thickness(self, thickness: int) -> None:
        self.drawing_thickness = max(1, min(10, thickness))
        self.drawing_thickness_changed.emit(self.drawing_thickness)

    # ═══════════════════════════════════════════════════════════════════════
    #  Screenshot
    # ═══════════════════════════════════════════════════════════════════════

    def take_screenshot(self, drawing_overlay: "DrawingOverlay",
                        save_path: str) -> bool:
        """Сохранить текущий кадр с аннотациями как PNG."""
        try:
            pixmap = self.pc.get_cached_pixmap(self.current_frame)
            if pixmap is None or pixmap.isNull():
                return False

            if drawing_overlay and drawing_overlay.has_drawings():
                result = drawing_overlay.render_to_pixmap(pixmap)
            else:
                result = pixmap.copy()

            os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
            return result.save(save_path, "PNG")

        except Exception as e:
            print(f"Screenshot error: {e}")
            return False

    def get_screenshot_filename(self) -> str:
        """Предложить имя файла для скриншота."""
        marker = self.get_current_marker()
        name = marker.event_name if marker else "frame"
        name = re.sub(r'[\\/:*?"<>|]+', "_", name)
        return f"screenshot_{name}_{self.current_frame}.png"

    # ═══════════════════════════════════════════════════════════════════════
    #  Marker editing (I/O points)
    # ═══════════════════════════════════════════════════════════════════════

    def set_in_point(self) -> None:
        """Установить начало сегмента на текущий кадр."""
        marker = self.get_current_marker()
        if not marker:
            return
        if self.current_frame < marker.end_frame:
            marker.start_frame = self.current_frame
            self._notify_marker_changed()

    def set_out_point(self) -> None:
        """Установить конец сегмента на текущий кадр."""
        marker = self.get_current_marker()
        if not marker:
            return
        if self.current_frame > marker.start_frame:
            marker.end_frame = self.current_frame
            self._notify_marker_changed()

    def update_note(self, text: str) -> None:
        """Обновить заметку текущего сегмента."""
        marker = self.get_current_marker()
        if marker:
            marker.note = text
            self._notify_marker_changed()

    def _notify_marker_changed(self) -> None:
        """Уведомить о изменении маркера."""
        try:
            self.mc.timeline_controller.markers_changed.emit()
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════
    #  Delegate actions
    # ═══════════════════════════════════════════════════════════════════════

    def open_segment_editor(self, marker_idx: int) -> None:
        if self.is_playing:
            self.pause()
        if hasattr(self.mc, 'open_segment_editor'):
            self.mc.open_segment_editor(marker_idx)

    def delete_marker(self, marker_idx: int) -> None:
        self.mc.delete_marker(marker_idx)

    # ═══════════════════════════════════════════════════════════════════════
    #  Cleanup
    # ═══════════════════════════════════════════════════════════════════════

    def cleanup(self) -> None:
        self._timer.stop()
        self.is_playing = False