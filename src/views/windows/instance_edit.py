"""
Instance Edit Window - Professional video segment editing window.
"""

from typing import Optional, List, Tuple
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame, QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QKeySequence, QAction, QPainter, QColor, QPen, QBrush

from models.domain.marker import Marker
from utils.time_utils import frames_to_time
from services.events.custom_event_manager import get_custom_event_manager


class VisualTimeline(QWidget):
    """Visual timeline with contextual zoom."""
    rangeChanged = Signal(int, int)
    seekRequested = Signal(int)

    def __init__(self, total_duration_frames, start_frame, end_frame, fps=30, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.total_video_frames = max(1, total_duration_frames)
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.current_frame = start_frame
        self.fps = fps

        self.padding_seconds = 10
        self.padding_frames = int(self.padding_seconds * self.fps)

        self.dragging_mode = None
        self.hover_mode = None
        self.margin_x = 15

        self.zoom_locked = False
        self.locked_visible_start = 0
        self.locked_visible_end = 0

    def _get_visible_range(self):
        if self.zoom_locked:
            return self.locked_visible_start, self.locked_visible_end
        visible_start = max(0, self.start_frame - self.padding_frames)
        visible_end = min(self.total_video_frames, self.end_frame + self.padding_frames)
        return visible_start, visible_end

    def lock_zoom(self):
        self.locked_visible_start, self.locked_visible_end = self._get_visible_range()
        self.zoom_locked = True

    def unlock_zoom(self):
        self.zoom_locked = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        vis_start, vis_end = self._get_visible_range()
        vis_duration = max(1, vis_end - vis_start)
        draw_w = w - 2 * self.margin_x
        bar_y = h // 2 - 4
        bar_h = 8

        def frame_to_x(f):
            return self.margin_x + ((f - vis_start) / vis_duration) * draw_w

        x_start = frame_to_x(self.start_frame)
        x_end = frame_to_x(self.end_frame)
        x_curr = frame_to_x(self.current_frame)

        painter.setBrush(QBrush(QColor("#333333")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.margin_x, bar_y, draw_w, bar_h, 4, 4)

        painter.setPen(QPen(QColor("#555555"), 1, Qt.SolidLine))
        grid_interval_frames = int(5 * self.fps)
        if grid_interval_frames > 0:
            start_grid = (vis_start // grid_interval_frames) * grid_interval_frames
            for frame in range(start_grid, vis_end + 1, grid_interval_frames):
                if vis_start <= frame <= vis_end:
                    x = self.margin_x + ((frame - vis_start) / vis_duration) * draw_w
                    painter.drawLine(int(x), bar_y, int(x), bar_y + bar_h)

        rect_x = max(self.margin_x, x_start)
        rect_w = min(self.margin_x + draw_w, x_end) - rect_x
        if rect_w > 0:
            painter.setBrush(QBrush(QColor("#1a4d7a")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(int(rect_x), bar_y, int(rect_w), bar_h)

        handle_h = 24
        handle_y = bar_y - (handle_h - bar_h) // 2
        painter.setPen(Qt.PenStyle.NoPen)

        if x_start >= self.margin_x:
            c = QColor("#FFFFFF") if self.hover_mode == 'start' or self.dragging_mode == 'start' else QColor("#CCCCCC")
            painter.setBrush(QBrush(c))
            painter.drawRoundedRect(int(x_start) - 4, handle_y, 4, handle_h, 2, 2)

        if x_end <= self.margin_x + draw_w:
            c = QColor("#FFFFFF") if self.hover_mode == 'end' or self.dragging_mode == 'end' else QColor("#CCCCCC")
            painter.setBrush(QBrush(c))
            painter.drawRoundedRect(int(x_end), handle_y, 4, handle_h, 2, 2)

        if self.margin_x <= x_curr <= self.margin_x + draw_w:
            painter.setPen(QPen(QColor("#FFFF00"), 3, Qt.SolidLine))
            painter.drawLine(int(x_curr), bar_y - 6, int(x_curr), bar_y + bar_h + 6)

    def _get_frame_from_x(self, x):
        vis_start, vis_end = self._get_visible_range()
        vis_duration = max(1, vis_end - vis_start)
        draw_w = self.width() - 2 * self.margin_x
        if draw_w <= 0:
            return 0
        return int(vis_start + ((x - self.margin_x) / draw_w) * vis_duration)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        x = event.position().x()
        frame = self._get_frame_from_x(x)
        vis_start, vis_end = self._get_visible_range()
        draw_w = self.width() - 2 * self.margin_x
        if draw_w <= 0:
            return
        frame_threshold = (12 / draw_w) * (vis_end - vis_start)

        if abs(frame - self.start_frame) < frame_threshold:
            self.dragging_mode = 'start'
        elif abs(frame - self.end_frame) < frame_threshold:
            self.dragging_mode = 'end'
        else:
            self.dragging_mode = 'playhead'
            self.seekRequested.emit(max(vis_start, min(frame, vis_end)))
        self.update()

    def mouseMoveEvent(self, event):
        x = event.position().x()
        frame = self._get_frame_from_x(x)
        vis_start, vis_end = self._get_visible_range()

        if self.dragging_mode == 'start':
            self.rangeChanged.emit(max(0, min(frame, self.end_frame - 1)), self.end_frame)
        elif self.dragging_mode == 'end':
            self.rangeChanged.emit(self.start_frame, max(self.start_frame + 1, min(frame, self.total_video_frames)))
        elif self.dragging_mode == 'playhead':
            self.seekRequested.emit(max(vis_start, min(frame, vis_end)))
        else:
            draw_w = self.width() - 2 * self.margin_x
            if draw_w > 0:
                ft = (12 / draw_w) * (vis_end - vis_start)
                if abs(frame - self.start_frame) < ft:
                    self.hover_mode = 'start'
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif abs(frame - self.end_frame) < ft:
                    self.hover_mode = 'end'
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                else:
                    self.hover_mode = None
                    self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging_mode = None
        self.update()

    def set_current_frame(self, frame):
        self.current_frame = frame
        self.update()

    def set_range(self, start, end):
        self.start_frame = start
        self.end_frame = end
        self.update()


class InstanceEditWindow(QDialog):
    """Segment editing window."""

    marker_updated = Signal()
    accepted = Signal()

    def __init__(self, marker: Marker, controller, filtered_markers=None,
                 current_marker_idx=0, parent=None):
        super().__init__(parent)
        self.marker = marker
        self.controller = controller
        self.instance_controller = controller.get_instance_edit_controller()
        self.fps = self.instance_controller.get_fps()

        self.filtered_markers = filtered_markers or []
        self.current_marker_idx = current_marker_idx
        self.total_video_frames = max(1, controller.get_total_frames())

        # FIX: Guard against recursive signal emission
        self._emitting_update = False

        # Debounce for seek
        self._seek_timer = QTimer(self)
        self._seek_timer.setSingleShot(True)
        self._seek_timer.setInterval(30)
        self._seek_timer.timeout.connect(self._do_deferred_seek)
        self._pending_seek_frame: Optional[int] = None

        event_manager = get_custom_event_manager()
        event_display_name = marker.event_name
        if event_manager:
            ev = event_manager.get_event(marker.event_name)
            if ev:
                event_display_name = ev.get_localized_name()

        progress = f" ({current_marker_idx + 1}/{len(filtered_markers)})" if filtered_markers else ""
        self.setWindowTitle(f"Instance Edit - {event_display_name}{progress}")
        self.resize(1000, 700)

        self.is_playing = False
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)
        self.loop_enabled = True
        self.active_point = 'in'

        self._setup_ui()
        self._setup_shortcuts()

        # Initialize controller
        self.instance_controller.set_marker(
            self.marker, self.filtered_markers, self.current_marker_idx
        )

        # FIX: Do NOT connect controller.marker_updated → window.marker_updated
        # That creates infinite recursion:
        # window.marker_updated → controller._on_external_marker_update
        #   → controller.marker_updated → window.marker_updated → LOOP!
        #
        # Instead, only connect controller signals for UI updates:
        self.instance_controller.playback_position_changed.connect(
            self._on_playback_position_changed
        )
        self.instance_controller.timeline_range_changed.connect(
            self._on_controller_range_changed
        )
        self.instance_controller.active_point_changed.connect(
            self._on_active_point_changed
        )

        try:
            self.controller.playback_controller.pixmap_changed.connect(
                self._on_main_pixmap_changed
            )
        except Exception:
            pass

        self._update_ui_from_marker()
        self._update_active_point_visual()
        self._update_navigation_buttons()
        self._display_current_frame()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_label, stretch=1)

        trim_panel = QHBoxLayout()
        self.lbl_start = QLabel("00:00")
        trim_panel.addWidget(self.lbl_start)

        self.timeline = VisualTimeline(
            self.total_video_frames, self.marker.start_frame,
            self.marker.end_frame, self.fps
        )
        self.timeline.rangeChanged.connect(self._on_timeline_drag)
        self.timeline.seekRequested.connect(self._on_timeline_seek)
        trim_panel.addWidget(self.timeline, stretch=1)

        self.lbl_end = QLabel("00:00")
        trim_panel.addWidget(self.lbl_end)
        layout.addLayout(trim_panel)

        controls_layout = QHBoxLayout()

        in_group = QFrame()
        in_layout = QHBoxLayout(in_group)
        in_layout.setContentsMargins(2, 2, 2, 2)
        in_layout.setSpacing(1)

        btn_in_minus = QPushButton("◀")
        btn_in_minus.setFixedWidth(24)
        btn_in_minus.clicked.connect(lambda: self._nudge_in(-1))
        in_layout.addWidget(btn_in_minus)
        in_layout.addWidget(QLabel(" IN "))
        btn_in_plus = QPushButton("▶")
        btn_in_plus.setFixedWidth(24)
        btn_in_plus.clicked.connect(lambda: self._nudge_in(1))
        in_layout.addWidget(btn_in_plus)
        controls_layout.addWidget(in_group)

        controls_layout.addStretch()

        self.btn_play = QPushButton("Play Loop")
        self.btn_play.clicked.connect(self._toggle_play)
        controls_layout.addWidget(self.btn_play)

        self.chk_loop = QCheckBox("Loop")
        self.chk_loop.setChecked(True)
        self.chk_loop.stateChanged.connect(lambda s: setattr(self, 'loop_enabled', bool(s)))
        controls_layout.addWidget(self.chk_loop)

        controls_layout.addStretch()

        out_group = QFrame()
        out_layout = QHBoxLayout(out_group)
        out_layout.setContentsMargins(2, 2, 2, 2)
        out_layout.setSpacing(1)

        btn_out_minus = QPushButton("◀")
        btn_out_minus.setFixedWidth(24)
        btn_out_minus.clicked.connect(lambda: self._nudge_out(-1))
        out_layout.addWidget(btn_out_minus)
        out_layout.addWidget(QLabel(" OUT "))
        btn_out_plus = QPushButton("▶")
        btn_out_plus.setFixedWidth(24)
        btn_out_plus.clicked.connect(lambda: self._nudge_out(1))
        out_layout.addWidget(btn_out_plus)
        controls_layout.addWidget(out_group)

        layout.addLayout(controls_layout)

        data_layout = QHBoxLayout()
        data_layout.addWidget(QLabel("Code:"))

        self.combo_code = QComboBox()
        event_manager = get_custom_event_manager()
        if event_manager:
            events = event_manager.get_all_events()
            current_index = 0
            for i, ev in enumerate(events):
                self.combo_code.addItem(ev.get_localized_name(), ev.name)
                if ev.name == self.marker.event_name:
                    current_index = i
            self.combo_code.setCurrentIndex(current_index)
        else:
            self.combo_code.addItem(self.marker.event_name, self.marker.event_name)

        self.combo_code.currentIndexChanged.connect(self._on_code_changed)
        data_layout.addWidget(self.combo_code)

        data_layout.addWidget(QLabel("Note:"))
        self.txt_note = QLineEdit()
        self.txt_note.setText(self.marker.note or "")
        self.txt_note.textChanged.connect(self._on_note_changed)
        data_layout.addWidget(self.txt_note)
        layout.addLayout(data_layout)

        buttons_layout = QHBoxLayout()
        if self.filtered_markers:
            self.btn_prev = QPushButton("◀ Предыдущий")
            self.btn_prev.setMaximumWidth(120)
            self.btn_prev.clicked.connect(self._navigate_previous)
            buttons_layout.addWidget(self.btn_prev)

            self.btn_next = QPushButton("Следующий ▶")
            self.btn_next.setMaximumWidth(120)
            self.btn_next.clicked.connect(self._navigate_next)
            buttons_layout.addWidget(self.btn_next)

        buttons_layout.addStretch()

        self.save_btn = QPushButton("✓ Сохранить")
        self.save_btn.setMaximumWidth(100)
        self.save_btn.clicked.connect(self._accept_changes)
        buttons_layout.addWidget(self.save_btn)
        layout.addLayout(buttons_layout)

    def _setup_shortcuts(self):
        shortcuts = [
            ("Set In", Qt.Key.Key_I, self._set_in_point),
            ("Set Out", Qt.Key.Key_O, self._set_out_point),
            ("Play/Pause", Qt.Key.Key_Space, self._toggle_play),
            ("Play/Pause K", Qt.Key.Key_K, self._toggle_play),
            ("Prev Frame", Qt.Key.Key_Left, lambda: self._step_frame(-1)),
            ("Prev Frame J", Qt.Key.Key_J, lambda: self._step_frame(-1)),
            ("Next Frame", Qt.Key.Key_Right, lambda: self._step_frame(1)),
            ("Next Frame L", Qt.Key.Key_L, lambda: self._step_frame(1)),
            ("Accept", Qt.Key.Key_Return, self._accept_changes),
            ("Accept Enter", Qt.Key.Key_Enter, self._accept_changes),
            ("Toggle Point", Qt.Key.Key_Tab, self._toggle_active_point),
            ("Close", Qt.Key.Key_Escape, self.close),
        ]
        for name, key, callback in shortcuts:
            self.addAction(QAction(name, self, shortcut=QKeySequence(key), triggered=callback))

        self.addAction(QAction("Jump Back", self, shortcut=QKeySequence("Shift+Left"),
                               triggered=lambda: self._step_frame(-10)))
        self.addAction(QAction("Jump Fwd", self, shortcut=QKeySequence("Shift+Right"),
                               triggered=lambda: self._step_frame(10)))
        self.addAction(QAction("Close W", self, shortcut=QKeySequence("Ctrl+W"),
                               triggered=self.close))

    # ──────────────────────────────────────────────────────────────────────────
    # Safe signal emission (prevents recursion)
    # ──────────────────────────────────────────────────────────────────────────

    def _emit_marker_updated(self):
        """Safely emit marker_updated with recursion guard."""
        if self._emitting_update:
            return
        self._emitting_update = True
        try:
            self.marker_updated.emit()
        finally:
            self._emitting_update = False

    # ──────────────────────────────────────────────────────────────────────────
    # Debounced seek
    # ──────────────────────────────────────────────────────────────────────────

    def _request_seek(self, frame: int):
        self._pending_seek_frame = frame
        if not self._seek_timer.isActive():
            self._seek_timer.start()

    def _do_deferred_seek(self):
        if self._pending_seek_frame is not None:
            frame = self._pending_seek_frame
            self._pending_seek_frame = None
            try:
                self.controller.playback_controller.seek_to_frame_immediate(frame)
            except Exception as e:
                print(f"Seek error: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Controller signal handlers
    # ──────────────────────────────────────────────────────────────────────────

    def _on_playback_position_changed(self, frame: int):
        self.timeline.set_current_frame(frame)

    def _on_controller_range_changed(self, start: int, end: int):
        self.marker.start_frame = start
        self.marker.end_frame = end
        self._update_ui_from_marker()

    def _on_active_point_changed(self, point: str):
        self.active_point = point
        self._update_active_point_visual()

    # ──────────────────────────────────────────────────────────────────────────
    # Timeline UI events
    # ──────────────────────────────────────────────────────────────────────────

    def _on_timeline_drag(self, start: int, end: int):
        self.marker.start_frame = start
        self.marker.end_frame = end
        self._update_ui_from_marker()
        self._emit_marker_updated()

    def _on_timeline_seek(self, frame: int):
        self._request_seek(frame)

    # ──────────────────────────────────────────────────────────────────────────
    # Nudge / Step / Set points
    # ──────────────────────────────────────────────────────────────────────────

    def _nudge_in(self, delta: int):
        new_start = max(0, self.marker.start_frame + delta)
        if new_start < self.marker.end_frame:
            self.marker.start_frame = new_start
            self._update_ui_from_marker()
            self._request_seek(new_start)
            self._emit_marker_updated()

    def _nudge_out(self, delta: int):
        new_end = min(self.total_video_frames, self.marker.end_frame + delta)
        if new_end > self.marker.start_frame:
            self.marker.end_frame = new_end
            self._update_ui_from_marker()
            self._request_seek(max(self.marker.start_frame, new_end - 1))
            self._emit_marker_updated()

    def _set_in_point(self):
        curr = self.controller.playback_controller.current_frame
        if curr < self.marker.end_frame:
            self.marker.start_frame = curr
            self._update_ui_from_marker()
            self._emit_marker_updated()

    def _set_out_point(self):
        curr = self.controller.playback_controller.current_frame
        if curr > self.marker.start_frame:
            self.marker.end_frame = curr
            self._update_ui_from_marker()
            self._emit_marker_updated()

    def _step_frame(self, frames: int):
        if self.is_playing:
            self._toggle_play()

        if self.active_point == 'in':
            new_start = max(0, min(self.marker.start_frame + frames, self.marker.end_frame - 1))
            if new_start != self.marker.start_frame:
                self.marker.start_frame = new_start
                self._update_ui_from_marker()
                self._request_seek(new_start)
                self._emit_marker_updated()
        else:
            new_end = max(self.marker.start_frame + 1, min(self.marker.end_frame + frames, self.total_video_frames))
            if new_end != self.marker.end_frame:
                self.marker.end_frame = new_end
                self._update_ui_from_marker()
                self._request_seek(max(self.marker.start_frame, new_end - 1))
                self._emit_marker_updated()

    # ──────────────────────────────────────────────────────────────────────────
    # Playback
    # ──────────────────────────────────────────────────────────────────────────

    def _toggle_play(self):
        if self.is_playing:
            self.playback_timer.stop()
            self.is_playing = False
            self.btn_play.setText("Play Loop")
        else:
            self.is_playing = True
            self.btn_play.setText("Pause")
            curr = self.controller.playback_controller.current_frame
            if curr >= self.marker.end_frame or curr < self.marker.start_frame:
                self.controller.playback_controller.seek_to_frame_immediate(self.marker.start_frame)
            interval = max(1, int(1000 / self.fps)) if self.fps > 0 else 33
            self.playback_timer.start(interval)

    def _on_playback_tick(self):
        try:
            current_frame = self.controller.playback_controller.current_frame + 1
            if self.loop_enabled and current_frame >= self.marker.end_frame:
                current_frame = self.marker.start_frame
            self.controller.playback_controller.seek_to_frame_immediate(current_frame)
            self.timeline.set_current_frame(current_frame)
            if not self.loop_enabled and current_frame >= self.marker.end_frame:
                self.playback_timer.stop()
                self.is_playing = False
                self.btn_play.setText("Play Loop")
        except Exception as e:
            print(f"Playback tick error: {e}")
            self.playback_timer.stop()
            self.is_playing = False

    # ──────────────────────────────────────────────────────────────────────────
    # Active point
    # ──────────────────────────────────────────────────────────────────────────

    def _toggle_active_point(self):
        self.active_point = 'out' if self.active_point == 'in' else 'in'
        self._update_active_point_visual()
        self.timeline.lock_zoom()
        active_frame = (
            self.marker.start_frame if self.active_point == 'in'
            else max(self.marker.start_frame, self.marker.end_frame - 1)
        )
        self._request_seek(active_frame)

    def _update_active_point_visual(self):
        if self.active_point == 'in':
            self.lbl_start.setStyleSheet("font-weight: bold; color: #00ff00;")
            self.lbl_end.setStyleSheet("font-weight: normal; color: #cccccc;")
        else:
            self.lbl_start.setStyleSheet("font-weight: normal; color: #cccccc;")
            self.lbl_end.setStyleSheet("font-weight: bold; color: #00ff00;")

    # ──────────────────────────────────────────────────────────────────────────
    # Navigation
    # ──────────────────────────────────────────────────────────────────────────

    def _navigate_previous(self):
        if not self.filtered_markers or self.current_marker_idx <= 0:
            return
        self._emit_marker_updated()
        self._switch_to_marker(self.filtered_markers[self.current_marker_idx - 1][1],
                               self.current_marker_idx - 1)

    def _navigate_next(self):
        if not self.filtered_markers or self.current_marker_idx >= len(self.filtered_markers) - 1:
            return
        self._emit_marker_updated()
        self._switch_to_marker(self.filtered_markers[self.current_marker_idx + 1][1],
                               self.current_marker_idx + 1)

    def _switch_to_marker(self, marker: Marker, idx: int):
        if self.is_playing:
            self._toggle_play()

        self.marker = marker
        self.current_marker_idx = idx

        self.instance_controller.set_marker(marker, self.filtered_markers, idx)

        event_manager = get_custom_event_manager()
        name = marker.event_name
        if event_manager:
            ev = event_manager.get_event(marker.event_name)
            if ev:
                name = ev.get_localized_name()
        progress = f" ({idx + 1}/{len(self.filtered_markers)})"
        self.setWindowTitle(f"Instance Edit - {name}{progress}")

        self.timeline.start_frame = marker.start_frame
        self.timeline.end_frame = marker.end_frame
        self.timeline.unlock_zoom()

        self._update_ui_from_marker()
        self._update_navigation_buttons()

        self.combo_code.blockSignals(True)
        for i in range(self.combo_code.count()):
            if self.combo_code.itemData(i) == marker.event_name:
                self.combo_code.setCurrentIndex(i)
                break
        self.combo_code.blockSignals(False)

        self.txt_note.blockSignals(True)
        self.txt_note.setText(marker.note or "")
        self.txt_note.blockSignals(False)

        self.controller.playback_controller.seek_to_frame_immediate(marker.start_frame)

    def _accept_changes(self):
        self._emit_marker_updated()
        self.accepted.emit()

        if hasattr(self.controller, 'timeline_controller'):
            self.controller.timeline_controller.refresh_view()

        if self.filtered_markers and self.current_marker_idx < len(self.filtered_markers) - 1:
            self._navigate_next()
        else:
            self.close()

    def _update_navigation_buttons(self):
        if hasattr(self, 'btn_prev'):
            self.btn_prev.setEnabled(self.current_marker_idx > 0)
        if hasattr(self, 'btn_next'):
            self.btn_next.setEnabled(self.current_marker_idx < len(self.filtered_markers) - 1)

    # ──────────────────────────────────────────────────────────────────────────
    # Data editing
    # ──────────────────────────────────────────────────────────────────────────

    def _on_code_changed(self, index: int):
        data = self.combo_code.currentData()
        if data and self.marker:
            self.marker.event_name = data
            event_manager = get_custom_event_manager()
            name = data
            if event_manager:
                ev = event_manager.get_event(data)
                if ev:
                    name = ev.get_localized_name()
            progress = f" ({self.current_marker_idx + 1}/{len(self.filtered_markers)})" if self.filtered_markers else ""
            self.setWindowTitle(f"Instance Edit - {name}{progress}")
            self._emit_marker_updated()

    def _on_note_changed(self, text: str):
        if self.marker:
            self.marker.note = text
            self._emit_marker_updated()

    # ──────────────────────────────────────────────────────────────────────────
    # Display
    # ──────────────────────────────────────────────────────────────────────────

    def _update_ui_from_marker(self):
        self.timeline.set_range(self.marker.start_frame, self.marker.end_frame)
        self.lbl_start.setText(frames_to_time(self.marker.start_frame, self.fps))
        self.lbl_end.setText(frames_to_time(self.marker.end_frame, self.fps))

    def _display_current_frame(self):
        frame_idx = self.controller.playback_controller.current_frame
        pixmap = None
        if hasattr(self.controller.playback_controller, "get_cached_pixmap"):
            pixmap = self.controller.playback_controller.get_cached_pixmap(frame_idx)
        if pixmap is not None:
            self._display_pixmap(pixmap)

    def _on_main_pixmap_changed(self, pixmap: QPixmap, frame_idx: int):
        if frame_idx != self.controller.playback_controller.current_frame:
            return
        self._display_pixmap(pixmap)

    def _display_pixmap(self, pixmap: QPixmap):
        if pixmap is None or pixmap.isNull():
            return
        scaled = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(scaled)

    def closeEvent(self, event):
        self.playback_timer.stop()
        self._seek_timer.stop()
        super().closeEvent(event)

    def resizeEvent(self, event):
        self._display_current_frame()
        super().resizeEvent(event)