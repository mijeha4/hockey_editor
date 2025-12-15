"""
Окно глубокого редактирования конкретного отрезка (Instance).
Замена EditSegmentDialog с интерактивным слайдером и логикой зацикливания.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QMouseEvent, QPixmap, QImage,
    QAction, QKeySequence, QPainterPath
)
import cv2
from typing import Optional

from ..models.marker import Marker
from ..utils.time_utils import frames_to_time
from ..utils.custom_events import get_custom_event_manager


class VisualTimeline(QWidget):
    """
    Визуальный таймлайн с контекстным масштабированием (Zoom).
    Показывает не весь матч, а окрестности отрезка.
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

        # НАСТРОЙКИ ЗУМА
        # Сколько секунд показывать до и после отрезка
        self.padding_seconds = 10
        self.padding_frames = int(self.padding_seconds * self.fps)

        self.dragging_mode = None
        self.hover_mode = None
        self.margin_x = 15

        # Фиксация масштаба для предотвращения нежелательного зума при редактировании
        self.zoom_locked = False
        self.locked_visible_start = 0
        self.locked_visible_end = 0

    def _get_visible_range(self):
        """Вычисляет, какой диапазон кадров сейчас виден на таймлайне."""
        if self.zoom_locked:
            # Возвращаем зафиксированную область
            return self.locked_visible_start, self.locked_visible_end

        # Центр видимой области - это центр текущего отрезка
        # Но мы динамически расширяем область, чтобы всегда видеть границы + запас

        # Минимальная видимая зона: Start - 10сек ... End + 10сек
        visible_start = max(0, self.start_frame - self.padding_frames)
        visible_end = min(self.total_video_frames, self.end_frame + self.padding_frames)

        return visible_start, visible_end

    def lock_zoom(self):
        """Зафиксировать текущую видимую область масштаба."""
        self.locked_visible_start, self.locked_visible_end = self._get_visible_range()
        self.zoom_locked = True

    def unlock_zoom(self):
        """Разблокировать масштаб."""
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

        # Функция перевода кадра в пиксель X (с учетом ЗУМА)
        def frame_to_x(f):
            # Нормализуем относительно видимого окна
            rel_f = f - vis_start
            ratio = rel_f / vis_duration
            return self.margin_x + (ratio * draw_w)

        x_start = frame_to_x(self.start_frame)
        x_end = frame_to_x(self.end_frame)
        x_curr = frame_to_x(self.current_frame)

        # 1. Фон (видимая область контекста)
        painter.setBrush(QBrush(QColor("#333333")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.margin_x, bar_y, draw_w, bar_h, 4, 4)

        # 1.5. Сетка времени (вертикальные линии)
        painter.setPen(QPen(QColor("#555555"), 1, Qt.SolidLine))
        # Рисуем линии каждые 5 секунд
        grid_interval_seconds = 5
        grid_interval_frames = int(grid_interval_seconds * self.fps)

        start_grid_frame = (vis_start // grid_interval_frames) * grid_interval_frames
        for frame in range(start_grid_frame, vis_end + 1, grid_interval_frames):
            if frame >= vis_start and frame <= vis_end:
                x = self.margin_x + ((frame - vis_start) / vis_duration) * draw_w
                painter.drawLine(int(x), int(bar_y), int(x), int(bar_y + bar_h))

        # 2. Активная зона (Сам клип)
        # Ограничиваем рисование, чтобы не вылезало за margin
        rect_x = max(self.margin_x, x_start)
        rect_w = min(self.margin_x + draw_w, x_end) - rect_x

        if rect_w > 0:
            painter.setBrush(QBrush(QColor("#1a4d7a"))) # Синий
            painter.drawRect(int(rect_x), int(bar_y), int(rect_w), int(bar_h))

        # 3. Ручки (Handles) - рисуем как скобки [ ]
        handle_w = 8
        handle_h = 24
        handle_y = bar_y - (handle_h - bar_h) // 2

        painter.setPen(Qt.PenStyle.NoPen)

        # Ручка IN
        if x_start >= self.margin_x:
            color = QColor("#FFFFFF") if (self.hover_mode == 'start' or self.dragging_mode == 'start') else QColor("#CCCCCC")
            painter.setBrush(QBrush(color))
            # Рисуем левую скобку
            painter.drawRoundedRect(int(x_start) - 4, int(handle_y), 4, int(handle_h), 2, 2) # Вертикаль
            # painter.drawRect(int(x_start), int(handle_y), 4, 2) # Верхний ус (опционально)
            # painter.drawRect(int(x_start), int(handle_y + handle_h - 2), 4, 2) # Нижний ус

        # Ручка OUT
        if x_end <= self.margin_x + draw_w:
            color = QColor("#FFFFFF") if (self.hover_mode == 'end' or self.dragging_mode == 'end') else QColor("#CCCCCC")
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(int(x_end), int(handle_y), 4, int(handle_h), 2, 2)

        # 4. Поплавок (Playhead) - индикатор текущей позиции воспроизведения
        if self.margin_x <= x_curr <= self.margin_x + draw_w:
            painter.setPen(QPen(QColor("#FFFF00"), 3, Qt.SolidLine))  # Желтая линия толщиной 3px
            painter.drawLine(int(x_curr), int(bar_y - 6), int(x_curr), int(bar_y + bar_h + 6))




    def _get_frame_from_x(self, x):
        vis_start, vis_end = self._get_visible_range()
        vis_duration = vis_end - vis_start

        draw_w = self.width() - 2 * self.margin_x
        if draw_w <= 0: return 0

        ratio = (x - self.margin_x) / draw_w
        # Не ограничиваем ratio жестко 0..1, чтобы можно было тянуть чуть за край (логику ограничим в mouseMove)
        frame = int(vis_start + (ratio * vis_duration))
        return frame

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton: return
        x = event.position().x()
        frame = self._get_frame_from_x(x)

        # Точность нажатия в пикселях
        pixel_threshold = 12
        # Переводим пиксели в кадры (зависит от текущего зума)
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
            self.seekRequested.emit(max(vis_start, min(frame, vis_end))) # Ограничиваем клик видимой зоной
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        x = event.position().x()
        frame = self._get_frame_from_x(x)
        vis_start, vis_end = self._get_visible_range()

        if self.dragging_mode == 'start':
            # Логика: Start не может быть > End
            new_start = min(frame, self.end_frame - 1)
            new_start = max(0, new_start) # Не меньше 0
            self.rangeChanged.emit(new_start, self.end_frame)

        elif self.dragging_mode == 'end':
            # Логика: End не может быть < Start
            new_end = max(frame, self.start_frame + 1)
            new_end = min(self.total_video_frames, new_end) # Не больше длины видео
            self.rangeChanged.emit(self.start_frame, new_end)

        elif self.dragging_mode == 'playhead':
            # Ограничиваем курсор видимой зоной для удобства
            seek_frame = max(vis_start, min(frame, vis_end))
            self.seekRequested.emit(seek_frame)

        else:
            # Hover эффект
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
    Окно глубокого редактирования конкретного отрезка (Instance).
    Функции: Loop playback, Trim In/Out, Edit Labels.
    """

    # Сигналы
    marker_updated = Signal()        # Маркер изменился
    accepted = Signal()              # Окно принято (сохранено)

    def __init__(self, marker: Marker, controller, filtered_markers=None, current_marker_idx=0, parent=None):
        super().__init__(parent)
        self.marker = marker  # Ссылка на редактируемый объект
        self.controller = controller
        self.fps = controller.get_fps() if controller.get_fps() > 0 else 30.0

        # Навигация между маркерами
        self.filtered_markers = filtered_markers or []  # Список (original_idx, marker) кортежей
        self.current_marker_idx = current_marker_idx  # Индекс текущего маркера в filtered_markers

        # Получаем полную длительность видео для слайдера
        self.total_video_frames = controller.get_total_frames()

        # Используем event_name для заголовка с прогрессом
        event_manager = get_custom_event_manager()
        event = event_manager.get_event(marker.event_name)
        event_display_name = event.get_localized_name() if event else marker.event_name

        # Добавляем прогресс, если есть отфильтрованные маркеры
        if filtered_markers:
            progress = f" ({current_marker_idx + 1}/{len(filtered_markers)})"
            title = f"Instance Edit - {event_display_name}{progress}"
        else:
            title = f"Instance Edit - {event_display_name}"

        self.setWindowTitle(title)
        self.resize(1000, 700)
        self.setStyleSheet(self._get_dark_stylesheet())

        # Состояние воспроизведения
        self.is_playing = False
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)
        self.loop_enabled = True

        # Активная точка редактирования (IN или OUT)
        self.active_point = 'in'  # По умолчанию IN (начало отрезка)

        self._setup_ui()
        self._setup_shortcuts()

        # Инициализация - устанавливаем playhead на начало отрезка (IN)
        self.controller.seek_frame(self.marker.start_frame)
        self._update_ui_from_marker()
        self._update_active_point_visual()  # Инициализируем визуальное выделение активной точки
        self._update_navigation_buttons()  # Обновляем состояние кнопок навигации
        self._display_current_frame()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 1. Видеоплеер
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; border: 1px solid #444;")
        self.video_label.setMinimumSize(640, 360)
        layout.addWidget(self.video_label, stretch=1)

        # 2. Панель Тримминга (Кастомный слайдер)
        trim_panel = QHBoxLayout()

        # Таймкоды слева
        self.lbl_start = QLabel("00:00")
        self.lbl_start.setStyleSheet("color: #FFFF00; font-weight: bold;")  # Желтый для IN
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
        self.lbl_end.setStyleSheet("color: #FFFF00; font-weight: bold;")
        trim_panel.addWidget(self.lbl_end)

        layout.addLayout(trim_panel)

        # 3. Кнопки управления (Nudge buttons)
        controls_layout = QHBoxLayout()

        # Группа IN (слева)
        in_group = QFrame()
        in_group.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")
        in_layout = QHBoxLayout(in_group)
        in_layout.setContentsMargins(2, 2, 2, 2) # Компактнее
        in_layout.setSpacing(1)

        btn_in_minus = QPushButton("◀") # Стрелка влево
        btn_in_minus.setToolTip("-1 кадр")
        btn_in_minus.setFixedWidth(24)
        btn_in_minus.clicked.connect(lambda: self._nudge_in(-1))

        lbl_in_title = QLabel(" IN ")
        lbl_in_title.setStyleSheet("font-weight: bold; color: #FFF; border: none;")
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
        out_group.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")
        out_layout = QHBoxLayout(out_group)
        out_layout.setContentsMargins(2, 2, 2, 2) # Компактнее
        out_layout.setSpacing(1)

        btn_out_minus = QPushButton("◀") # Стрелка влево
        btn_out_minus.setToolTip("-1 кадр")
        btn_out_minus.setFixedWidth(24)
        btn_out_minus.clicked.connect(lambda: self._nudge_out(-1))

        lbl_out_title = QLabel(" OUT ")
        lbl_out_title.setStyleSheet("font-weight: bold; color: #FFF; border: none;")
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
        # Заполните данными из event_manager
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
            self.btn_prev.setMaximumWidth(120)
            self.btn_prev.setStyleSheet("""
                QPushButton {
                    background-color: #333333;
                    color: white;
                    border: 1px solid #555555;
                    padding: 8px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #444444;
                }
                QPushButton:pressed {
                    background-color: #222222;
                }
                QPushButton:disabled {
                    background-color: #222222;
                    color: #666666;
                }
            """)
            self.btn_prev.clicked.connect(self._navigate_previous)
            buttons_layout.addWidget(self.btn_prev)

            # Следующий клип
            self.btn_next = QPushButton("Следующий ▶")
            self.btn_next.setMaximumWidth(120)
            self.btn_next.setStyleSheet("""
                QPushButton {
                    background-color: #333333;
                    color: white;
                    border: 1px solid #555555;
                    padding: 8px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #444444;
                }
                QPushButton:pressed {
                    background-color: #222222;
                }
                QPushButton:disabled {
                    background-color: #222222;
                    color: #666666;
                }
            """)
            self.btn_next.clicked.connect(self._navigate_next)
            buttons_layout.addWidget(self.btn_next)

            buttons_layout.addStretch()
        else:
            buttons_layout.addStretch()

        # Кнопка Сохранить (зеленая, акцентная)
        self.save_btn = QPushButton("✓ Сохранить")
        self.save_btn.setMaximumWidth(100)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5016;
                color: white;
                border: 1px solid #3d6b1f;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d6b1f;
            }
            QPushButton:pressed {
                background-color: #1f3a0f;
            }
        """)
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
        if abs(self.controller.get_current_frame_idx() - start) < abs(self.controller.get_current_frame_idx() - end):
             self.controller.seek_frame(start)
        else:
             self.controller.seek_frame(end)
        self._display_current_frame()

    def _on_timeline_seek(self, frame):
        """Клик по слайдеру для перемотки"""
        self.controller.seek_frame(frame)
        self._display_current_frame()

    def _nudge_in(self, delta):
        new_start = max(0, self.marker.start_frame + delta)
        if new_start < self.marker.end_frame:
            self.marker.start_frame = new_start
            self._update_ui_from_marker()
            self.controller.seek_frame(new_start)
            self._display_current_frame()
            self.marker_updated.emit()

    def _nudge_out(self, delta):
        new_end = min(self.total_video_frames, self.marker.end_frame + delta)
        if new_end > self.marker.start_frame:
            self.marker.end_frame = new_end
            self._update_ui_from_marker()
            self.controller.seek_frame(new_end)
            self._display_current_frame()
            self.marker_updated.emit()

    def _set_in_point(self):
        curr = self.controller.get_current_frame_idx()
        if curr < self.marker.end_frame:
            self.marker.start_frame = curr
            self._update_ui_from_marker()
            self.marker_updated.emit()

    def _set_out_point(self):
        curr = self.controller.get_current_frame_idx()
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
                self.controller.seek_frame(new_start)
                self._display_current_frame()
                self.marker_updated.emit()
        else:  # active_point == 'out'
            # Перемещаем OUT точку
            new_end = max(self.marker.start_frame + 1, min(self.marker.end_frame + frames, self.total_video_frames - 1))
            if new_end != self.marker.end_frame:
                self.marker.end_frame = new_end
                self._update_ui_from_marker()
                self.controller.seek_frame(new_end)
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
            curr = self.controller.get_current_frame_idx()
            if curr >= self.marker.end_frame or curr < self.marker.start_frame:
                self.controller.seek_frame(self.marker.start_frame)

            interval = int(1000 / self.fps)
            self.playback_timer.start(interval)

    def _on_playback_tick(self):
        # 1. Двигаем кадр вперед
        self.controller.processor.advance_frame()
        curr = self.controller.get_current_frame_idx()

        # 2. Логика Loop
        if self.loop_enabled:
            if curr >= self.marker.end_frame:
                self.controller.seek_frame(self.marker.start_frame)
                curr = self.marker.start_frame

        # 3. Обновляем UI
        self._display_current_frame()
        self.timeline.set_current_frame(curr)

    def _display_current_frame(self):
        """Отобразить текущий кадр (адаптировано из PreviewWindow)"""
        frame = self.controller.processor.get_current_frame()
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
        self.controller.seek_frame(active_frame)
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
                # IN активна - зеленая рамка
                in_group.setStyleSheet("background-color: #2a2a2a; border: 2px solid #00AA00; border-radius: 4px;")
                out_group.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")
            else:
                # OUT активна - зеленая рамка
                in_group.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")
                out_group.setStyleSheet("background-color: #2a2a2a; border: 2px solid #00AA00; border-radius: 4px;")

    def closeEvent(self, event):
        self.playback_timer.stop()
        super().closeEvent(event)

    def resizeEvent(self, event):
        self._display_current_frame()
        super().resizeEvent(event)

    def _get_dark_stylesheet(self):
        """Тёмный стиль (адаптирован из PreviewWindow)"""
        return """
        QMainWindow, QWidget {
            background-color: #1a1a1a;
            color: #ffffff;
        }
        QPushButton {
            background-color: #333333;
            color: white;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #444444;
        }
        QLineEdit, QComboBox {
            background-color: #333333;
            color: white;
            border: 1px solid #555555;
            padding: 3px;
            border-radius: 3px;
        }
        QLabel {
            color: #ffffff;
        }
        QCheckBox {
            color: #ffffff;
        }
        """
