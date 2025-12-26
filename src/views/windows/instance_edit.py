"""
Instance Edit Window - Professional video segment editing window.

Provides advanced interface for precise segment editing with visual timeline,
loop playback, hotkeys, and professional NLE-style controls.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame, QCheckBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QKeySequence, QAction

# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.marker import Marker
    from utils.time_utils import frames_to_time
    from utils.custom_events import get_custom_event_manager
except ImportError:
    # Для случаев, когда запускаем из src/
    try:
        from ...models.domain.marker import Marker
    except ImportError:
        # Fallback для Marker
        class Marker:
            def __init__(self, start_frame=0, end_frame=100, event_name="test", note=""):
                self.start_frame = start_frame
                self.end_frame = end_frame
                self.event_name = event_name
                self.note = note

    try:
        from ...utils.time_utils import frames_to_time
    except ImportError:
        # Fallback для frames_to_time
        def frames_to_time(frames: int, fps: float) -> str:
            if fps <= 0:
                return "00:00"
            seconds = frames / fps
            minutes = int(seconds) // 60
            secs = int(seconds) % 60
            return f"{minutes:02d}:{secs:02d}"

    try:
        from ...utils.custom_events import get_custom_event_manager
    except ImportError:
        # Fallback для get_custom_event_manager
        def get_custom_event_manager():
            return None


class VisualTimeline(QWidget):
    """
    Visual timeline with contextual zoom (Zoom).
    Shows not the entire match, but the surroundings of the segment.
    """
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

        # ZOOM SETTINGS
        # How many seconds to show before and after the segment
        self.padding_seconds = 10
        self.padding_frames = int(self.padding_seconds * self.fps)

        self.dragging_mode = None
        self.hover_mode = None
        self.margin_x = 15

        # Zoom lock to prevent unwanted zoom when editing
        self.zoom_locked = False
        self.locked_visible_start = 0
        self.locked_visible_end = 0

    def _get_visible_range(self):
        """Calculate which frame range is currently visible on the timeline."""
        if self.zoom_locked:
            # Return locked area
            return self.locked_visible_start, self.locked_visible_end

        # Center of visible area is the center of current segment
        # But we dynamically expand the area to always see boundaries + margin

        # Minimum visible area: Start - 10sec ... End + 10sec
        visible_start = max(0, self.start_frame - self.padding_frames)
        visible_end = min(self.total_video_frames, self.end_frame + self.padding_frames)

        return visible_start, visible_end

    def lock_zoom(self):
        """Lock current zoom area."""
        self.locked_visible_start, self.locked_visible_end = self._get_visible_range()
        self.zoom_locked = True

    def unlock_zoom(self):
        """Unlock zoom."""
        self.zoom_locked = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        vis_start, vis_end = self._get_visible_range()
        vis_duration = vis_end - vis_start
        if vis_duration == 0: vis_duration = 1

        draw_w = w - 2 * self.margin_x
        bar_y = h // 2 - 4
        bar_h = 8

        # Function to translate frame to X pixel (with ZOOM)
        def frame_to_x(f):
            # Normalize relative to visible window
            rel_f = f - vis_start
            ratio = rel_f / vis_duration
            return self.margin_x + (ratio * draw_w)

        x_start = frame_to_x(self.start_frame)
        x_end = frame_to_x(self.end_frame)
        x_curr = frame_to_x(self.current_frame)

        # 1. Context background (visible area)
        painter.setBrush(QBrush(QColor("#333333")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.margin_x, bar_y, draw_w, bar_h, 4, 4)

        # 1.5. Time grid (vertical lines)
        painter.setPen(QPen(QColor("#555555"), 1, Qt.SolidLine))
        # Draw lines every 5 seconds
        grid_interval_seconds = 5
        grid_interval_frames = int(grid_interval_seconds * self.fps)

        start_grid_frame = (vis_start // grid_interval_frames) * grid_interval_frames
        for frame in range(start_grid_frame, vis_end + 1, grid_interval_frames):
            if frame >= vis_start and frame <= vis_end:
                x = self.margin_x + ((frame - vis_start) / vis_duration) * draw_w
                painter.drawLine(int(x), int(bar_y), int(x), int(bar_y + bar_h))

        # 2. Active zone (The clip itself)
        # Limit drawing so it doesn't go beyond margin
        rect_x = max(self.margin_x, x_start)
        rect_w = min(self.margin_x + draw_w, x_end) - rect_x

        if rect_w > 0:
            painter.setBrush(QBrush(QColor("#1a4d7a"))) # Blue
            painter.drawRect(int(rect_x), int(bar_y), int(rect_w), int(bar_h))

        # 3. Handles (Handles) - draw as [ ] brackets
        handle_w = 8
        handle_h = 24
        handle_y = bar_y - (handle_h - bar_h) // 2

        painter.setPen(Qt.PenStyle.NoPen)

        # IN handle
        if x_start >= self.margin_x:
            color = QColor("#FFFFFF") if (self.hover_mode == 'start' or self.dragging_mode == 'start') else QColor("#CCCCCC")
            painter.setBrush(QBrush(color))
            # Draw left bracket
            painter.drawRoundedRect(int(x_start) - 4, int(handle_y), 4, int(handle_h), 2, 2) # Vertical
            # painter.drawRect(int(x_start), int(handle_y), 4, 2) # Upper whisker (optional)
            # painter.drawRect(int(x_start), int(handle_y + handle_h - 2), 4, 2) # Lower whisker

        # OUT handle
        if x_end <= self.margin_x + draw_w:
            color = QColor("#FFFFFF") if (self.hover_mode == 'end' or self.dragging_mode == 'end') else QColor("#CCCCCC")
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(int(x_end), int(handle_y), 4, int(handle_h), 2, 2)

        # 4. Playhead (Playhead) - current playback position indicator
        if self.margin_x <= x_curr <= self.margin_x + draw_w:
            painter.setPen(QPen(QColor("#FFFF00"), 3, Qt.SolidLine))  # Yellow line 3px thick
            painter.drawLine(int(x_curr), int(bar_y - 6), int(x_curr), int(bar_y + bar_h + 6))

    def _get_frame_from_x(self, x):
        vis_start, vis_end = self._get_visible_range()
        vis_duration = vis_end - vis_start

        draw_w = self.width() - 2 * self.margin_x
        if draw_w <= 0: return 0

        ratio = (x - self.margin_x) / draw_w
        # Don't limit ratio strictly 0..1 so you can pull a bit beyond the edge (logic limited in mouseMove)
        frame = int(vis_start + (ratio * vis_duration))
        return frame

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton: return
        x = event.position().x()
        frame = self._get_frame_from_x(x)

        # Click precision in pixels
        pixel_threshold = 12
        # Convert pixels to frames (depends on current zoom)
        vis_start, vis_end = self._get_visible_range()
        frame_threshold = (pixel_threshold / (self.width() - 2 * self.margin_x)) * (vis_end - vis_start)

        dist_start = abs(frame - self.start_frame)
        dist_end = abs(frame - self.end_frame)

        if dist_start < frame_threshold:
            self.dragging_mode = 'start'
        elif dist_end < frame_threshold:
            self.dragging_mode = 'end'
        else:
            self.dragging_mode = 'playhead'
            self.seekRequested.emit(max(vis_start, min(frame, vis_end))) # Limit click to visible area
        self.update()

    def mouseMoveEvent(self, event):
        x = event.position().x()
        frame = self._get_frame_from_x(x)
        vis_start, vis_end = self._get_visible_range()

        if self.dragging_mode == 'start':
            # Logic: Start cannot be > End
            new_start = min(frame, self.end_frame - 1)
            new_start = max(0, new_start) # Not less than 0
            self.rangeChanged.emit(new_start, self.end_frame)

        elif self.dragging_mode == 'end':
            # Logic: End cannot be < Start
            new_end = max(frame, self.start_frame + 1)
            new_end = min(self.total_video_frames, new_end) # Not more than video length
            self.rangeChanged.emit(self.start_frame, new_end)

        elif self.dragging_mode == 'playhead':
            # Limit cursor to visible area for convenience
            seek_frame = max(vis_start, min(frame, vis_end))
            self.seekRequested.emit(seek_frame)

        else:
            # Hover effect
            pixel_threshold = 12
            frame_threshold = (pixel_threshold / (self.width() - 2 * self.margin_x)) * (vis_end - vis_start)

            if abs(frame - self.start_frame) < frame_threshold:
                self.hover_mode = 'start'
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif abs(frame - self.end_frame) < frame_threshold:
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


class InstanceEditWindow(QMainWindow):
    """
    Deep segment editing window (Instance).
    Functions: Loop playback, Trim In/Out, Edit Labels.
    """

    # Signals
    marker_updated = Signal()        # Marker changed
    accepted = Signal()              # Window accepted (saved)

    def __init__(self, marker: Marker, controller, filtered_markers=None, current_marker_idx=0, parent=None):
        super().__init__(parent)
        self.marker = marker  # Reference to edited object
        self.controller = controller
        self.fps = controller.get_fps() if controller.get_fps() > 0 else 30.0

        # Navigation between markers
        self.filtered_markers = filtered_markers or []  # List (original_idx, marker) tuples
        self.current_marker_idx = current_marker_idx  # Index of current marker in filtered_markers

        # Get full video duration for slider
        self.total_video_frames = controller.get_total_frames()

        # Use event_name for title with progress
        event_manager = get_custom_event_manager()
        event = event_manager.get_event(marker.event_name)
        event_display_name = event.get_localized_name() if event else marker.event_name

        # Add progress if there are filtered markers
        if filtered_markers:
            progress = f" ({current_marker_idx + 1}/{len(filtered_markers)})"
            title = f"Instance Edit - {event_display_name}{progress}"
        else:
            title = f"Instance Edit - {event_display_name}"

        self.setWindowTitle(title)
        self.resize(1000, 700)

        # Playback state
        self.is_playing = False
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)
        self.loop_enabled = True

        # Active editing point (IN or OUT)
        self.active_point = 'in'  # Default IN (segment start)

        self._setup_ui()
        self._setup_shortcuts()

        # Initialize - set playhead to segment start (IN)
        self.controller.playback_controller.seek_to_frame(self.marker.start_frame)
        self._update_ui_from_marker()
        self._update_active_point_visual()  # Initialize visual highlighting of active point
        self._update_navigation_buttons()  # Update navigation button states
        self._display_current_frame()

    def _setup_ui(self):
        """Создать интерфейс."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 1. Видеоплеер
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 360)
        layout.addWidget(self.video_label, stretch=1)

        # 2. Панель Тримминга (Кастомный слайдер)
        trim_panel = QHBoxLayout()

        # Таймкоды слева
        self.lbl_start = QLabel("00:00")
        self.lbl_start.setProperty("class", "time-label")
        trim_panel.addWidget(self.lbl_start)

        # Слайдер
        self.timeline = VisualTimeline(self.total_video_frames,
                                     self.marker.start_frame,
                                     self.marker.end_frame,
                                     self.fps)
        self.timeline.rangeChanged.connect(self._on_timeline_range_changed)
        self.timeline.seekRequested.connect(self._on_timeline_seek)
        trim_panel.addWidget(self.timeline, stretch=1)

        # Таймкоды справа
        self.lbl_end = QLabel("00:00")
        self.lbl_end.setProperty("class", "time-label")
        trim_panel.addWidget(self.lbl_end)

        layout.addLayout(trim_panel)

        # 3. Кнопки управления (Nudge buttons)
        controls_layout = QHBoxLayout()

        # Группа IN (слева)
        in_group = QFrame()
        in_layout = QHBoxLayout(in_group)
        in_layout.setContentsMargins(2, 2, 2, 2) # Компактнее
        in_layout.setSpacing(1)

        btn_in_minus = QPushButton("◀") # Стрелка влево
        btn_in_minus.setToolTip("-1 кадр")
        btn_in_minus.setFixedWidth(24)
        btn_in_minus.clicked.connect(lambda: self._nudge_in(-1))

        lbl_in_title = QLabel(" IN ")
        lbl_in_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_in_plus = QPushButton("▶") # Стрелка вправо
        btn_in_plus.setToolTip("+1 кадр")
        btn_in_plus.setFixedWidth(24)
        btn_in_plus.clicked.connect(lambda: self._nudge_in(1))

        in_layout.addWidget(btn_in_minus)
        in_layout.addWidget(lbl_in_title)
        in_layout.addWidget(btn_in_plus)
        controls_layout.addWidget(in_group)

        controls_layout.addStretch()

        # Play Controls
        self.btn_play = QPushButton("Play Loop")
        self.btn_play.clicked.connect(self._toggle_play)

        self.chk_loop = QCheckBox("Loop")
        self.chk_loop.setChecked(True)
        self.chk_loop.stateChanged.connect(lambda s: setattr(self, 'loop_enabled', bool(s)))

        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.chk_loop)

        controls_layout.addStretch()

        # Группа OUT (справа)
        out_group = QFrame()
        out_layout = QHBoxLayout(out_group)
        out_layout.setContentsMargins(2, 2, 2, 2) # Компактнее
        out_layout.setSpacing(1)

        btn_out_minus = QPushButton("◀") # Стрелка влево
        btn_out_minus.setToolTip("-1 кадр")
        btn_out_minus.setFixedWidth(24)
        btn_out_minus.clicked.connect(lambda: self._nudge_out(-1))

        lbl_out_title = QLabel(" OUT ")
        lbl_out_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_out_plus = QPushButton("▶") # Стрелка вправо
        btn_out_plus.setToolTip("+1 кадр")
        btn_out_plus.setFixedWidth(24)
        btn_out_plus.clicked.connect(lambda: self._nudge_out(1))

        out_layout.addWidget(btn_out_minus)
        out_layout.addWidget(lbl_out_title)
        out_layout.addWidget(btn_out_plus)
        controls_layout.addWidget(out_group)

        layout.addLayout(controls_layout)

        # 4. Редактор данных (Data Editor)
        data_layout = QHBoxLayout()

        # Тип события (Code)
        data_layout.addWidget(QLabel("Code:"))
        self.combo_code = QComboBox()
        # Заполнить данными из event_manager
        event_manager = get_custom_event_manager()
        events = event_manager.get_all_events()
        for event in events:
            display_name = event.get_localized_name()
            self.combo_code.addItem(display_name, event.name)
        # Найти текущий event_name
        current_index = 0
        for i, event in enumerate(events):
            if event.name == self.marker.event_name:
                current_index = i
                break
        self.combo_code.setCurrentIndex(current_index)
        self.combo_code.currentTextChanged.connect(self._on_code_changed)
        data_layout.addWidget(self.combo_code)

        # Заметки (Labels)
        data_layout.addWidget(QLabel("Note:"))
        self.txt_note = QLineEdit()
        self.txt_note.setText(self.marker.note)
        self.txt_note.textChanged.connect(self._on_note_changed)
        data_layout.addWidget(self.txt_note)

        layout.addLayout(data_layout)

        # 5. Кнопки действий
        buttons_layout = QHBoxLayout()

        # Кнопки навигации (если есть отфильтрованные маркеры)
        if self.filtered_markers:
            # Предыдущий клип
            self.btn_prev = QPushButton("◀ Предыдущий")
            self.btn_prev.setProperty("class", "nav-button")
            self.btn_prev.setMaximumWidth(120)
            self.btn_prev.clicked.connect(self._navigate_previous)
            buttons_layout.addWidget(self.btn_prev)

            # Следующий клип
            self.btn_next = QPushButton("Следующий ▶")
            self.btn_next.setProperty("class", "nav-button")
            self.btn_next.setMaximumWidth(120)
            self.btn_next.clicked.connect(self._navigate_next)
            buttons_layout.addWidget(self.btn_next)

            buttons_layout.addStretch()
        else:
            buttons_layout.addStretch()

        # Кнопка Сохранить (зеленая, акцентная)
        self.save_btn = QPushButton("✓ Сохранить")
        self.save_btn.setProperty("class", "save-button")
        self.save_btn.setMaximumWidth(100)
        self.save_btn.clicked.connect(self._accept_changes)
        buttons_layout.addWidget(self.save_btn)

        layout.addLayout(buttons_layout)

    def _setup_shortcuts(self):
        """Настройка горячих клавиш (Sportscode / NLE style)."""
        # 1. In / Out
        self.addAction(QAction("Set In", self, shortcut=QKeySequence(Qt.Key.Key_I), triggered=self._set_in_point))
        self.addAction(QAction("Set Out", self, shortcut=QKeySequence(Qt.Key.Key_O), triggered=self._set_out_point))

        # 2. Воспроизведение (Play/Pause) - Пробел и K
        self.addAction(QAction("Play/Pause", self, shortcut=QKeySequence(Qt.Key.Key_Space), triggered=self._toggle_play))
        self.addAction(QAction("Play/Pause K", self, shortcut=QKeySequence(Qt.Key.Key_K), triggered=self._toggle_play))

        # 3. Покадровое перемещение (Стрелки и J/L)
        # Влево (Назад)
        self.addAction(QAction("Prev Frame Arrow", self, shortcut=QKeySequence(Qt.Key.Key_Left), triggered=lambda: self._step_frame(-1)))
        self.addAction(QAction("Prev Frame J", self, shortcut=QKeySequence(Qt.Key.Key_J), triggered=lambda: self._step_frame(-1)))

        # Вправо (Вперед)
        self.addAction(QAction("Next Frame Arrow", self, shortcut=QKeySequence(Qt.Key.Key_Right), triggered=lambda: self._step_frame(1)))
        self.addAction(QAction("Next Frame L", self, shortcut=QKeySequence(Qt.Key.Key_L), triggered=lambda: self._step_frame(1)))

        # 4. Быстрое перемещение (Shift + Стрелки) - 10 кадров
        self.addAction(QAction("Jump Back", self, shortcut=QKeySequence("Shift+Left"), triggered=lambda: self._step_frame(-10)))
        self.addAction(QAction("Jump Fwd", self, shortcut=QKeySequence("Shift+Right"), triggered=lambda: self._step_frame(10)))

        # 5. Сохранение и закрытие
        self.addAction(QAction("Accept", self, shortcut=QKeySequence(Qt.Key.Key_Return), triggered=self._accept_changes))
        self.addAction(QAction("Accept Enter", self, shortcut=QKeySequence(Qt.Key.Key_Enter), triggered=self._accept_changes))

        # 6. Переключение активной точки (Tab)
        self.addAction(QAction("Toggle Active Point", self, shortcut=QKeySequence(Qt.Key.Key_Tab), triggered=self._toggle_active_point))

        # 7. Закрытие
        self.addAction(QAction("Close", self, shortcut=QKeySequence(Qt.Key.Key_Escape), triggered=self.close))
        self.addAction(QAction("Close W", self, shortcut=QKeySequence("Ctrl+W"), triggered=self.close))

    # --- Logic ---

    def _on_timeline_range_changed(self, start, end):
        """Вызывается когда тянем ручки на слайдере"""
        self.marker.start_frame = start
        self.marker.end_frame = end
        self._update_ui_from_marker()
        self.marker_updated.emit()  # Уведомляем систему

        # Если меняем начало - перематываем туда, чтобы видеть кадр
        if abs(self.controller.playback_controller.current_frame - start) < abs(self.controller.playback_controller.current_frame - end):
             self.controller.playback_controller.seek_to_frame(start)
        else:
             self.controller.playback_controller.seek_to_frame(end)
        self._display_current_frame()

    def _on_timeline_seek(self, frame):
        """Клик по слайдеру для перемотки"""
        self.controller.playback_controller.seek_to_frame(frame)
        self._display_current_frame()

    def _nudge_in(self, delta):
        new_start = max(0, self.marker.start_frame + delta)
        if new_start < self.marker.end_frame:
            self.marker.start_frame = new_start
            self._update_ui_from_marker()
            self.controller.playback_controller.seek_to_frame(new_start)
            self._display_current_frame()
            self.marker_updated.emit()

    def _nudge_out(self, delta):
        new_end = min(self.total_video_frames, self.marker.end_frame + delta)
        if new_end > self.marker.start_frame:
            self.marker.end_frame = new_end
            self._update_ui_from_marker()
            self.controller.playback_controller.seek_to_frame(new_end)
            self._display_current_frame()
            self.marker_updated.emit()

    def _set_in_point(self):
        curr = self.controller.playback_controller.current_frame
        if curr < self.marker.end_frame:
            self.marker.start_frame = curr
            self._update_ui_from_marker()
            self.marker_updated.emit()

    def _set_out_point(self):
        curr = self.controller.playback_controller.current_frame
        if curr > self.marker.start_frame:
            self.marker.end_frame = curr
            self._update_ui_from_marker()
            self.marker_updated.emit()

    def _step_frame(self, frames):
        """Перемещение активной точки редактирования (IN или OUT) и синхронизация playhead."""
        # Если видео играло, ставим на паузу (обычно так удобнее для покадрового)
        if self.is_playing:
            self._toggle_play()

        if self.active_point == 'in':
            # Перемещаем IN точку
            new_start = max(0, min(self.marker.start_frame + frames, self.marker.end_frame - 1))
            if new_start != self.marker.start_frame:
                self.marker.start_frame = new_start
                self._update_ui_from_marker()
                self.controller.playback_controller.seek_to_frame(new_start)
                self._display_current_frame()
                self.marker_updated.emit()
        else:  # active_point == 'out'
            # Перемещаем OUT точку
            new_end = max(self.marker.start_frame + 1, min(self.marker.end_frame + frames, self.total_video_frames - 1))
            if new_end != self.marker.end_frame:
                self.marker.end_frame = new_end
                self._update_ui_from_marker()
                self.controller.playback_controller.seek_to_frame(new_end)
                self._display_current_frame()
                self.marker_updated.emit()

    def _navigate_previous(self):
        """Перейти к предыдущему маркеру в отфильтрованном списке."""
        if not self.filtered_markers or self.current_marker_idx <= 0:
            return

        # Автоматически сохранить текущие изменения
        self.marker_updated.emit()

        # Получить предыдущий маркер
        prev_idx = self.current_marker_idx - 1
        original_marker_idx, prev_marker = self.filtered_markers[prev_idx]

        # Создать новое окно редактирования
        self._open_marker_window(prev_marker, prev_idx)

    def _navigate_next(self):
        """Перейти к следующему маркеру в отфильтрованном списке."""
        if not self.filtered_markers or self.current_marker_idx >= len(self.filtered_markers) - 1:
            return

        # Автоматически сохранить текущие изменения
        self.marker_updated.emit()

        # Получить следующий маркер
        next_idx = self.current_marker_idx + 1
        original_marker_idx, next_marker = self.filtered_markers[next_idx]

        # Создать новое окно редактирования
        self._open_marker_window(next_marker, next_idx)

    def _open_marker_window(self, marker, marker_idx):
        """Открыть новое окно редактирования для указанного маркера."""
        # Закрыть текущее окно
        self.close()

        # Создать новое окно с тем же parent (main_window)
        parent = self.parent()
        if parent and hasattr(parent, 'instance_edit_window'):
            # Очистить ссылку на старое окно
            if hasattr(parent.instance_edit_window, '_marker_idx'):
                old_marker_idx = parent.instance_edit_window._marker_idx
                # Отключить старый сигнал
                try:
                    parent.instance_edit_window.marker_updated.disconnect()
                except:
                    pass

            # Создать новое окно
            parent.instance_edit_window = InstanceEditWindow(
                marker, self.controller, self.filtered_markers, marker_idx, parent
            )
            parent.instance_edit_window._marker_idx = marker_idx  # Для обратной совместимости
            parent.instance_edit_window.marker_updated.connect(
                lambda: parent._on_instance_updated(parent.instance_edit_window._marker_idx)
            )
            parent.instance_edit_window.show()

    def _accept_changes(self):
        """Сохранить изменения и перейти к следующему маркеру или закрыть окно."""
        # Финальное обновление маркера
        self.marker_updated.emit()

        # Сигнал о принятии изменений
        self.accepted.emit()

        # Проверить, есть ли следующий маркер
        if self.filtered_markers and self.current_marker_idx < len(self.filtered_markers) - 1:
            # Есть следующий маркер - перейти к нему
            self._navigate_next()
        else:
            # Это последний маркер - закрыть окно
            self.close()

    def _update_ui_from_marker(self):
        # Обновляем слайдер
        self.timeline.set_range(self.marker.start_frame, self.marker.end_frame)
        # Обновляем тексты
        self.lbl_start.setText(frames_to_time(self.marker.start_frame, self.fps))
        self.lbl_end.setText(frames_to_time(self.marker.end_frame, self.fps))

    def _toggle_play(self):
        if self.is_playing:
            self.playback_timer.stop()
            self.is_playing = False
            self.btn_play.setText("Play Loop")
        else:
            self.is_playing = True
            self.btn_play.setText("Pause")
            # Если мы в конце клипа, прыгаем в начало
            curr = self.controller.playback_controller.current_frame
            if curr >= self.marker.end_frame or curr < self.marker.start_frame:
                self.controller.playback_controller.seek_to_frame(self.marker.start_frame)

            interval = int(1000 / self.fps)
            self.playback_timer.start(interval)

    def _on_playback_tick(self):
        # 1. Двигаем кадр вперед
        self.controller.playback_controller.advance_frame()
        curr = self.controller.playback_controller.current_frame

        # 2. Логика Loop
        if self.loop_enabled:
            if curr >= self.marker.end_frame:
                self.controller.playback_controller.seek_to_frame(self.marker.start_frame)
                curr = self.marker.start_frame

        # 3. Обновляем UI
        self._display_current_frame()
        self.timeline.set_current_frame(curr)

    def _display_current_frame(self):
        """Отобразить текущий кадр (адаптировано из PreviewWindow)"""
        frame = self.controller.video_service.get_current_frame()
        if frame is None:
            return

        # Конвертировать BGR в RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # Масштабировать
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)

        # Центрировать изображение в контейнере
        container_width = self.video_label.width()
        container_height = self.video_label.height()
        pixmap_width = scaled_pixmap.width()
        pixmap_height = scaled_pixmap.height()

        x = (container_width - pixmap_width) // 2
        y = (container_height - pixmap_height) // 2

        self.video_label.setGeometry(x, y, pixmap_width, pixmap_height)
        self.video_label.setPixmap(scaled_pixmap)

    def _on_code_changed(self, text):
        # Получить event_name из combo box data
        current_data = self.combo_code.currentData()
        if current_data:
            self.marker.event_name = current_data
            # Обновить заголовок
            event_manager = get_custom_event_manager()
            event = event_manager.get_event(current_data)
            event_display_name = event.get_localized_name() if event else current_data
            self.setWindowTitle(f"Instance Edit - {event_display_name}")
            self.marker_updated.emit()

    def _on_note_changed(self, text):
        self.marker.note = text
        self.marker_updated.emit()

    def _toggle_active_point(self):
        """Переключение активной точки редактирования между IN и OUT."""
        self.active_point = 'out' if self.active_point == 'in' else 'in'
        self._update_active_point_visual()

        # Фиксируем масштаб при переключении, чтобы предотвратить нежелательное масштабирование
        self.timeline.lock_zoom()

        # Перемещаем playhead к новой активной точке
        active_frame = self.marker.start_frame if self.active_point == 'in' else self.marker.end_frame
        self.controller.playback_controller.seek_to_frame(active_frame)
        self._display_current_frame()

    def _update_navigation_buttons(self):
        """Обновление состояния кнопок навигации (включены/отключены)."""
        if not hasattr(self, 'btn_prev') or not hasattr(self, 'btn_next'):
            return

        # Кнопка "Предыдущий" активна, если есть предыдущий маркер
        self.btn_prev.setEnabled(self.current_marker_idx > 0)

        # Кнопка "Следующий" активна, если есть следующий маркер
        self.btn_next.setEnabled(self.current_marker_idx < len(self.filtered_markers) - 1)

    def _update_active_point_visual(self):
        """Обновление визуального выделения активной точки (IN или OUT)."""
        # Найдем группы IN и OUT в layout
        controls_layout = self.findChild(QHBoxLayout)
        if not controls_layout:
            return

        # Найдем группы по индексам (IN - индекс 0, OUT - индекс 4)
        in_group = controls_layout.itemAt(0).widget() if controls_layout.count() > 0 else None
        out_group = controls_layout.itemAt(4).widget() if controls_layout.count() > 4 else None

        if in_group and out_group:
            if self.active_point == 'in':
                # IN активна - добавить класс in-active
                in_group.setProperty("class", "in-active")
                out_group.setProperty("class", "")
            else:
                # OUT активна - добавить класс out-active
                in_group.setProperty("class", "")
                out_group.setProperty("class", "out-active")

            # Обновить стили
            in_group.style().unpolish(in_group)
            in_group.style().polish(in_group)
            out_group.style().unpolish(out_group)
            out_group.style().polish(out_group)

    def closeEvent(self, event):
        self.playback_timer.stop()
        super().closeEvent(event)

    def resizeEvent(self, event):
        self._display_current_frame()
        super().resizeEvent(event)

    def _create_video_preview(self, parent_layout: QVBoxLayout) -> None:
        """Create video preview section."""
        # Video display placeholder
        self.video_label = QLabel("Video Preview")
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #000000;
                color: #666666;
                border: 2px solid #444444;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        parent_layout.addWidget(self.video_label, stretch=1)

    def _create_timeline_section(self, parent_layout: QVBoxLayout) -> None:
        """Create timeline editing section with progress bar and time labels."""
        # Time labels layout
        time_layout = QHBoxLayout()

        self.start_time_label = QLabel("00:00")
        self.start_time_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        time_layout.addWidget(self.start_time_label)

        time_layout.addStretch()

        self.end_time_label = QLabel("00:00")
        self.end_time_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        time_layout.addWidget(self.end_time_label)

        parent_layout.addLayout(time_layout)

        # Timeline progress bar (placeholder for dual-handle slider)
        self.timeline_bar = QProgressBar()
        self.timeline_bar.setRange(0, 100)
        self.timeline_bar.setValue(50)
        self.timeline_bar.setTextVisible(False)
        self.timeline_bar.setFixedHeight(20)
        self.timeline_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #444444;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #1a4d7a;
                border-radius: 3px;
            }
        """)
        parent_layout.addWidget(self.timeline_bar)

        # Note about dual handles
        handles_note = QLabel("Note: Dual-handle slider would be implemented here")
        handles_note.setStyleSheet("color: #888888; font-style: italic;")
        parent_layout.addWidget(handles_note)

    def _create_trim_controls(self, parent_layout: QVBoxLayout) -> None:
        """Create trim controls with IN/OUT buttons and play loop."""
        controls_layout = QHBoxLayout()

        # IN group
        in_group = QFrame()
        in_group.setFrameStyle(QFrame.Shape.Box)
        in_layout = QHBoxLayout(in_group)
        in_layout.setContentsMargins(5, 5, 5, 5)
        in_layout.setSpacing(2)

        in_label = QLabel("IN")
        in_label.setStyleSheet("font-weight: bold;")
        in_layout.addWidget(in_label)

        self.in_minus_btn = QPushButton("-1")
        self.in_minus_btn.setFixedWidth(30)
        self.in_minus_btn.clicked.connect(self._on_in_minus)
        in_layout.addWidget(self.in_minus_btn)

        self.set_in_btn = QPushButton("SET IN")
        self.set_in_btn.clicked.connect(self._on_set_in)
        in_layout.addWidget(self.set_in_btn)

        self.in_plus_btn = QPushButton("+1")
        self.in_plus_btn.setFixedWidth(30)
        self.in_plus_btn.clicked.connect(self._on_in_plus)
        in_layout.addWidget(self.in_plus_btn)

        controls_layout.addWidget(in_group)

        controls_layout.addStretch()

        # Play Loop button (center)
        self.play_loop_btn = QPushButton("Play Loop")
        self.play_loop_btn.setFixedWidth(100)
        self.play_loop_btn.clicked.connect(self._on_play_loop)
        controls_layout.addWidget(self.play_loop_btn)

        controls_layout.addStretch()

        # OUT group
        out_group = QFrame()
        out_group.setFrameStyle(QFrame.Shape.Box)
        out_layout = QHBoxLayout(out_group)
        out_layout.setContentsMargins(5, 5, 5, 5)
        out_layout.setSpacing(2)

        out_label = QLabel("OUT")
        out_label.setStyleSheet("font-weight: bold;")
        out_layout.addWidget(out_label)

        self.out_minus_btn = QPushButton("-1")
        self.out_minus_btn.setFixedWidth(30)
        self.out_minus_btn.clicked.connect(self._on_out_minus)
        out_layout.addWidget(self.out_minus_btn)

        self.set_out_btn = QPushButton("SET OUT")
        self.set_out_btn.clicked.connect(self._on_set_out)
        out_layout.addWidget(self.set_out_btn)

        self.out_plus_btn = QPushButton("+1")
        self.out_plus_btn.setFixedWidth(30)
        self.out_plus_btn.clicked.connect(self._on_out_plus)
        out_layout.addWidget(self.out_plus_btn)

        controls_layout.addWidget(out_group)

        parent_layout.addLayout(controls_layout)

    def _create_data_section(self, parent_layout: QVBoxLayout) -> None:
        """Create data editing section with event type and notes."""
        data_layout = QHBoxLayout()

        # Event type (Code)
        data_layout.addWidget(QLabel("Code:"))

        self.event_combo = QComboBox()
        self.event_combo.addItems(["Attack", "Defense", "Change"])
        self.event_combo.setFixedWidth(120)
        self.event_combo.currentTextChanged.connect(self._on_event_changed)
        data_layout.addWidget(self.event_combo)

        data_layout.addStretch()

        # Notes
        data_layout.addWidget(QLabel("Note:"))

        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("Enter note...")
        self.note_edit.textChanged.connect(self._on_note_changed)
        data_layout.addWidget(self.note_edit)

        parent_layout.addLayout(data_layout)

    def _create_footer(self, parent_layout: QVBoxLayout) -> None:
        """Create footer with navigation and save buttons."""
        footer_layout = QHBoxLayout()

        # Previous button
        self.previous_btn = QPushButton("Previous")
        self.previous_btn.clicked.connect(self._on_previous)
        footer_layout.addWidget(self.previous_btn)

        footer_layout.addStretch()

        # Save button (green styling)
        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #00AA00;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #008800;
            }
            QPushButton:pressed {
                background-color: #006600;
            }
        """)
        self.save_btn.clicked.connect(self._on_save)
        footer_layout.addWidget(self.save_btn)

        footer_layout.addStretch()

        # Next button
        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self._on_next)
        footer_layout.addWidget(self.next_btn)

        parent_layout.addLayout(footer_layout)

    # Event handlers
    def _on_in_minus(self) -> None:
        """Handle IN minus button."""
        if self.marker:
            self.marker.start_frame = max(0, self.marker.start_frame - 1)
            self._update_ui()

    def _on_set_in(self) -> None:
        """Handle SET IN button."""
        # Placeholder - would set IN point to current playback position
        print("SET IN clicked")

    def _on_in_plus(self) -> None:
        """Handle IN plus button."""
        if self.marker:
            self.marker.start_frame = min(self.marker.end_frame - 1, self.marker.start_frame + 1)
            self._update_ui()

    def _on_out_minus(self) -> None:
        """Handle OUT minus button."""
        if self.marker:
            self.marker.end_frame = max(self.marker.start_frame + 1, self.marker.end_frame - 1)
            self._update_ui()

    def _on_set_out(self) -> None:
        """Handle SET OUT button."""
        # Placeholder - would set OUT point to current playback position
        print("SET OUT clicked")

    def _on_out_plus(self) -> None:
        """Handle OUT plus button."""
        if self.marker:
            self.marker.end_frame = min(self.total_frames, self.marker.end_frame + 1)
            self._update_ui()

    def _on_play_loop(self) -> None:
        """Handle Play Loop button."""
        # Placeholder - would start/stop loop playback
        print("Play Loop clicked")

    def _on_event_changed(self, event_name: str) -> None:
        """Handle event type change."""
        if self.marker:
            self.marker.event_name = event_name

    def _on_note_changed(self, note: str) -> None:
        """Handle note change."""
        if self.marker:
            self.marker.note = note

    def _on_previous(self) -> None:
        """Handle Previous button."""
        self.previous_requested.emit()

    def _on_save(self) -> None:
        """Handle Save button."""
        self.save_requested.emit()
        self.accept()

    def _on_next(self) -> None:
        """Handle Next button."""
        self.next_requested.emit()

    def _update_ui(self) -> None:
        """Update UI elements based on current marker data."""
        if not self.marker:
            return

        # Update time labels
        start_seconds = self.marker.start_frame / self.fps
        end_seconds = self.marker.end_frame / self.fps

        self.start_time_label.setText("02d")
        self.end_time_label.setText("02d")

        # Update progress bar (simplified representation)
        if self.total_frames > 0:
            progress = int((self.marker.start_frame + self.marker.end_frame) / 2 / self.total_frames * 100)
            self.timeline_bar.setValue(progress)

        # Update event combo
        index = self.event_combo.findText(self.marker.event_name)
        if index >= 0:
            self.event_combo.setCurrentIndex(index)

        # Update note
        self.note_edit.setText(self.marker.note)

    # Public methods
    def load_marker(self, marker: Marker) -> None:
        """Load marker data into the dialog.

        Args:
            marker: Marker object to edit
        """
        self.marker = marker
        self._update_ui()

    def get_result(self) -> Optional[Marker]:
        """Get the edited marker result.

        Returns:
            Updated Marker object or None if cancelled
        """
        return self.marker

    def set_video_fps(self, fps: float) -> None:
        """Set video FPS for time calculations.

        Args:
            fps: Frames per second
        """
        self.fps = fps
        self._update_ui()

    def set_total_frames(self, total_frames: int) -> None:
        """Set total video frames.

        Args:
            total_frames: Total number of frames in video
        """
        self.total_frames = total_frames

    def set_video_image(self, pixmap: QPixmap) -> None:
        """Set video preview image.

        Args:
            pixmap: Video frame pixmap
        """
        self.video_label.setPixmap(pixmap)
