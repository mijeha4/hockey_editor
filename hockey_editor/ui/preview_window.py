"""
Preview Window - просмотр и воспроизведение отрезков (PySide6).
Немодальное окно с видеоплеером и списком отрезков.
"""

import cv2
import numpy as np
from typing import Optional
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QImage, QFont, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QListView,
    QCheckBox, QComboBox, QGroupBox, QSpinBox, QLineEdit, QButtonGroup,
    QTextEdit, QTimeEdit, QFormLayout,
    QFrame, QSizePolicy
)
from .event_list_model import MarkersListModel
from .event_card_delegate import EventCardDelegate
from ..models.marker import Marker, EventType
from .drawing_overlay import DrawingOverlay, DrawingTool


class EventCard(QFrame):
    """Карточка события с информацией и кнопками действий."""

    # Сигналы
    play_requested = Signal(int)  # marker_idx
    edit_requested = Signal(int)  # marker_idx
    delete_requested = Signal(int)  # marker_idx

    def __init__(self, marker_idx: int, marker: Marker, fps: float, parent=None):
        super().__init__(parent)
        self.marker_idx = marker_idx
        self.marker = marker
        self.fps = fps

        # Set up the card as a QFrame with class for QSS styling
        self.setProperty("class", "EventCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._setup_ui()
        self._update_colors()

    def _setup_ui(self):
        """Создать интерфейс карточки с новой структурой."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # ===== TOP ROW: Index | Start Time | Duration =====
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)

        # Index (#1)
        self.id_label = QLabel(f"#{self.marker_idx + 1}")
        self.id_label.setStyleSheet("color: @muted_text; font-size: @font_size_small; font-weight: bold;")
        top_layout.addWidget(self.id_label)

        # Start Time (00:00)
        start_time = self._format_time(self.marker.start_frame / self.fps if self.fps > 0 else 0)
        self.time_label = QLabel(start_time)
        self.time_label.setStyleSheet("color: @muted_text; font-size: @font_size_small; font-family: @font_family_mono;")
        top_layout.addWidget(self.time_label)

        # Duration (05s)
        duration_frames = self.marker.end_frame - self.marker.start_frame
        duration_time = self._format_time(duration_frames / self.fps if self.fps > 0 else 0)
        self.duration_label = QLabel(duration_time)
        self.duration_label.setStyleSheet("color: @muted_text; font-size: @font_size_small; font-family: @font_family_mono;")
        top_layout.addWidget(self.duration_label)

        top_layout.addStretch()
        layout.addLayout(top_layout)

        # ===== MIDDLE ROW: Event Name with Color Indicator =====
        event_layout = QHBoxLayout()
        event_layout.setSpacing(8)

        # Colored circle indicator
        self.color_indicator = QLabel()
        self.color_indicator.setFixedSize(12, 12)
        self.color_indicator.setStyleSheet("border-radius: 6px;")
        event_layout.addWidget(self.color_indicator)

        # Event name (large, bold, word wrap enabled)
        from ..utils.custom_events import get_custom_event_manager
        event_manager = get_custom_event_manager()
        event = event_manager.get_event(self.marker.event_name)
        event_name = event.get_localized_name() if event else self.marker.event_name
        self.event_label = QLabel(event_name)
        self.event_label.setStyleSheet("color: @primary_text; font-size: @font_size_large; font-weight: bold;")
        self.event_label.setWordWrap(True)
        self.event_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        event_layout.addWidget(self.event_label, 1)

        layout.addLayout(event_layout)

        # ===== BOTTOM ROW: Action Buttons (Right Aligned) =====
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()  # Push buttons to the right

        # Edit button
        self.edit_btn = QPushButton("✏️")
        self.edit_btn.setFixedSize(28, 24)
        self.edit_btn.setToolTip("Редактировать событие")
        self.edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.marker_idx))
        buttons_layout.addWidget(self.edit_btn)

        # Delete button
        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setFixedSize(28, 24)
        self.delete_btn.setToolTip("Удалить событие")
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.marker_idx))
        buttons_layout.addWidget(self.delete_btn)

        layout.addLayout(buttons_layout)

    def _update_colors(self):
        """Обновить цвета маркера и текста."""
        from ..utils.custom_events import get_custom_event_manager
        event_manager = get_custom_event_manager()
        event = event_manager.get_event(self.marker.event_name)

        if event:
            color = event.get_qcolor()
            self.color_indicator.setStyleSheet(f"""
                background-color: {color.name()};
                border-radius: 6px;
                border: 1px solid {color.darker(120).name()};
            """)
        else:
            self.color_indicator.setStyleSheet("""
                background-color: #666666;
                border-radius: 6px;
                border: 1px solid #444444;
            """)

    def set_active(self, is_active: bool):
        """Установить активное состояние (подсветка)."""
        # Если состояние не изменилось - выходим (оптимизация)
        if self.property("active") == is_active:
            return

        # 1. Меняем свойство
        self.setProperty("active", is_active)

        # 2. ВАЖНО: Заставляем Qt пересчитать стили!
        # Без этого цвет рамки не изменится
        self.style().unpolish(self)
        self.style().polish(self)

        # 3. Принудительная перерисовка
        self.update()

    def update_marker_info(self, marker: Marker, fps: float):
        """Обновить информацию о маркере в карточке."""
        self.marker = marker
        self.fps = fps

        # Update index
        self.id_label.setText(f"#{self.marker_idx + 1}")

        # Update start time
        start_time = self._format_time(marker.start_frame / fps if fps > 0 else 0)
        self.time_label.setText(start_time)

        # Update duration
        duration_frames = marker.end_frame - marker.start_frame
        duration_time = self._format_time(duration_frames / fps if fps > 0 else 0)
        self.duration_label.setText(duration_time)

        # Update event name
        from ..utils.custom_events import get_custom_event_manager
        event_manager = get_custom_event_manager()
        event = event_manager.get_event(marker.event_name)
        event_name = event.get_localized_name() if event else marker.event_name
        self.event_label.setText(event_name)

        # Update colors
        self._update_colors()

    def mouseDoubleClickEvent(self, event):
        """Обработка двойного клика - воспроизведение."""
        super().mouseDoubleClickEvent(event)
        self.play_requested.emit(self.marker_idx)

    def _format_time(self, seconds: float) -> str:
        """Форматировать время MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"





class PreviewWindow(QMainWindow):
    """
    Окно предпросмотра отрезков.
    Содержит видеоплеер и список отрезков с фильтрацией.
    """
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("🎬 Кинотеатр событий - Презентация тренерам")
        self.setGeometry(100, 100, 1400, 800)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # Немодальное окно

        # Параметры воспроизведения
        self.current_marker_idx = 0
        self.is_playing = False
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)
        self.frame_time_ms = 33  # ~30 FPS

        # Инициализация фильтров
        self._init_filters()

        # Создание модели и делегата для списка маркеров
        self.markers_model = MarkersListModel(self)
        self.markers_delegate = EventCardDelegate(self)
        self.markers_delegate.play_clicked.connect(self._on_card_play_requested)
        self.markers_delegate.edit_clicked.connect(self._on_card_edit_requested)
        self.markers_delegate.delete_clicked.connect(self._on_card_delete_requested)

        self._setup_ui()
        self._setup_shortcuts()
        self._update_speed_combo()
        self._update_marker_list()

        # Подключить сигнал изменения событий
        from ..utils.custom_events import get_custom_event_manager
        self.event_manager = get_custom_event_manager()
        self.event_manager.events_changed.connect(self._on_events_changed)

        # Connect to controller's playback time changed signal for active card highlighting
        self.controller.playback_time_changed.connect(self._on_playback_time_changed)

    def _on_playback_time_changed(self, frame_idx: int):
        """Handle playback time changes to highlight active event cards."""
        # Find which card should be active based on current frame
        active_marker_idx = None

        # Проверяем все маркеры в модели
        for row in range(self.markers_model.rowCount()):
            original_idx, marker = self.markers_model.get_marker_at(row)
            if marker and marker.start_frame <= frame_idx <= marker.end_frame:
                active_marker_idx = original_idx
                break

        # Update current_marker_idx if we found an active marker
        if active_marker_idx is not None:
            self.current_marker_idx = active_marker_idx

        # Update card highlighting
        self._update_active_card_highlight()

    def _init_filters(self):
        """Инициализация состояния фильтров."""
        self.filter_event_types = set()  # Множество выбранных типов событий
        self.filter_has_notes = False    # Фильтр по наличию заметок
        self.filter_min_duration = 0     # Минимальная длительность (секунды)
        self.filter_max_duration = 0     # Максимальная длительность (секунды)
        self.filter_notes_search = ""    # Поиск по тексту заметок

    def _setup_filters(self, parent_layout):
        """Создать элементы управления фильтрами."""
        # Контейнер для фильтров
        filters_layout = QVBoxLayout()
        filters_layout.setSpacing(3)

        # Первая строка: тип события + заметки
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(5)

        # Фильтр по типу события
        event_label = QLabel("Тип:")
        event_label.setMaximumWidth(25)
        row1_layout.addWidget(event_label)

        self.event_filter_combo = QComboBox()
        self.event_filter_combo.setToolTip("Фильтр по типу события")
        self.event_filter_combo.setMaximumWidth(100)
        self.event_filter_combo.currentTextChanged.connect(self._on_event_filter_changed)
        row1_layout.addWidget(self.event_filter_combo)

        # Чекбокс для фильтра заметок
        self.notes_filter_checkbox = QCheckBox("Заметки")
        self.notes_filter_checkbox.setToolTip("Показывать только отрезки с заметками")
        self.notes_filter_checkbox.stateChanged.connect(self._on_notes_filter_changed)
        row1_layout.addWidget(self.notes_filter_checkbox)

        # Кнопка сброса фильтров
        reset_btn = QPushButton("Сброс")
        reset_btn.setMaximumWidth(45)
        reset_btn.setToolTip("Сбросить все фильтры")
        reset_btn.clicked.connect(self._reset_filters)
        row1_layout.addWidget(reset_btn)

        filters_layout.addLayout(row1_layout)

        # Вторая строка: поиск по заметкам
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(5)

        search_label = QLabel("Поиск:")
        search_label.setMaximumWidth(40)
        row2_layout.addWidget(search_label)

        self.notes_search_edit = QLineEdit()
        self.notes_search_edit.setPlaceholderText("Поиск в заметках...")
        self.notes_search_edit.setToolTip("Поиск по тексту заметок")
        self.notes_search_edit.setMaximumWidth(120)
        self.notes_search_edit.textChanged.connect(self._on_notes_search_changed)
        row2_layout.addWidget(self.notes_search_edit)

        row2_layout.addStretch()
        filters_layout.addLayout(row2_layout)

        parent_layout.addLayout(filters_layout)

        # Заполнить фильтр событий
        self._update_event_filter()

    def _update_event_filter(self):
        """Обновить список доступных типов событий в фильтре."""
        self.event_filter_combo.blockSignals(True)
        self.event_filter_combo.clear()

        # Добавить опцию "Все"
        self.event_filter_combo.addItem("Все", None)

        # Добавить все доступные типы событий
        from ..utils.custom_events import get_custom_event_manager
        event_manager = get_custom_event_manager()
        events = event_manager.get_all_events()
        for event in events:
            localized_name = event.get_localized_name()
            self.event_filter_combo.addItem(localized_name, event.name)

        self.event_filter_combo.blockSignals(False)

    def _on_event_filter_changed(self):
        """Обработка изменения фильтра типов событий."""
        current_data = self.event_filter_combo.currentData()
        if current_data is None:  # "Все"
            self.filter_event_types.clear()
        else:
            self.filter_event_types = {current_data}

        self._update_marker_list()

    def _on_notes_filter_changed(self):
        """Обработка изменения фильтра заметок."""
        self.filter_has_notes = self.notes_filter_checkbox.isChecked()
        self._update_marker_list()

    def _on_notes_search_changed(self):
        """Обработка изменения поиска по заметкам."""
        self.filter_notes_search = self.notes_search_edit.text().strip().lower()
        self._update_marker_list()

    def _reset_filters(self):
        """Сбросить все фильтры."""
        self.event_filter_combo.blockSignals(True)
        self.event_filter_combo.setCurrentIndex(0)  # "Все"
        self.event_filter_combo.blockSignals(False)

        self.notes_filter_checkbox.setChecked(False)
        self.notes_search_edit.clear()

        self.filter_event_types.clear()
        self.filter_has_notes = False
        self.filter_notes_search = ""

        self._update_marker_list()

    def _on_events_changed(self):
        """Обработка изменения событий - обновить фильтр событий."""
        self._update_event_filter()



    def keyPressEvent(self, event):
        """Обработка горячих клавиш для быстрого редактирования маркеров."""
        # Защита от конфликтов: не обрабатывать горячие клавиши если фокус в поле ввода
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, (QLineEdit, QTextEdit, QTimeEdit, QSpinBox)):
            super().keyPressEvent(event)
            return

        # Для карточек используем текущий активный маркер
        if not self.controller.markers or self.current_marker_idx >= len(self.controller.markers):
            super().keyPressEvent(event)
            return

        marker = self.controller.markers[self.current_marker_idx]
        fps = self.controller.get_fps()
        if fps <= 0:
            super().keyPressEvent(event)
            return

        current_frame = self.controller.get_current_frame_idx()
        key = event.key()

        # I - установить начало маркера (In-point)
        if key == Qt.Key.Key_I:
            marker.start_frame = current_frame
            if marker.start_frame > marker.end_frame:
                marker.end_frame = marker.start_frame + int(fps)  # Минимум 1 секунда
            self.controller.markers_changed.emit()
            self._update_marker_list()
            event.accept()
            return

        # O - установить конец маркера (Out-point)
        elif key == Qt.Key.Key_O:
            marker.end_frame = current_frame
            if marker.end_frame < marker.start_frame:
                marker.start_frame = max(0, marker.end_frame - int(fps))  # Минимум 1 секунда
            self.controller.markers_changed.emit()
            self._update_marker_list()
            event.accept()
            return

        # Delete - удалить маркер
        elif key == Qt.Key.Key_Delete:
            self.controller.delete_marker(self.current_marker_idx)
            self._update_marker_list()
            event.accept()
            return

        # Shift + стрелки - сдвиг всего маркера
        elif event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            shift_frames = 0
            if key == Qt.Key.Key_Left:
                shift_frames = -int(fps)  # -1 секунда
            elif key == Qt.Key.Key_Right:
                shift_frames = int(fps)   # +1 секунда

            if shift_frames != 0:
                # Проверить границы видео
                total_frames = self.controller.get_total_frames()
                new_start = max(0, marker.start_frame + shift_frames)
                new_end = min(total_frames - 1, marker.end_frame + shift_frames)

                # Сдвинуть только если не выходит за границы
                if new_start >= 0 and new_end < total_frames:
                    marker.start_frame = new_start
                    marker.end_frame = new_end
                    self.controller.markers_changed.emit()
                    self._update_marker_list()
                event.accept()
                return

        # Передать событие дальше если не обработали
        super().keyPressEvent(event)



    def _setup_drawing_toolbar(self, parent_layout):
        """Создать панель инструментов рисования."""
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(5)

        # Группа кнопок инструментов
        self.drawing_tool_group = QButtonGroup(self)
        self.drawing_tool_group.buttonClicked.connect(self._on_drawing_tool_changed)

        # Кнопка выбора инструмента (курсор)
        cursor_btn = QPushButton("👆")
        cursor_btn.setMaximumWidth(35)
        cursor_btn.setToolTip("Выбрать (отключить рисование)")
        cursor_btn.setCheckable(True)
        cursor_btn.setChecked(True)  # По умолчанию выбран курсор
        self.drawing_tool_group.addButton(cursor_btn, 0)
        toolbar_layout.addWidget(cursor_btn)

        # Кнопка линии
        line_btn = QPushButton("📏")
        line_btn.setMaximumWidth(35)
        line_btn.setToolTip("Линия")
        line_btn.setCheckable(True)
        self.drawing_tool_group.addButton(line_btn, 1)
        toolbar_layout.addWidget(line_btn)

        # Кнопка прямоугольника
        rect_btn = QPushButton("▭")
        rect_btn.setMaximumWidth(35)
        rect_btn.setToolTip("Прямоугольник")
        rect_btn.setCheckable(True)
        self.drawing_tool_group.addButton(rect_btn, 2)
        toolbar_layout.addWidget(rect_btn)

        # Кнопка круга
        circle_btn = QPushButton("○")
        circle_btn.setMaximumWidth(35)
        circle_btn.setToolTip("Круг")
        circle_btn.setCheckable(True)
        self.drawing_tool_group.addButton(circle_btn, 3)
        toolbar_layout.addWidget(circle_btn)

        # Кнопка стрелки
        arrow_btn = QPushButton("➤")
        arrow_btn.setMaximumWidth(35)
        arrow_btn.setToolTip("Стрелка")
        arrow_btn.setCheckable(True)
        self.drawing_tool_group.addButton(arrow_btn, 4)
        toolbar_layout.addWidget(arrow_btn)

        toolbar_layout.addSpacing(10)

        # Выбор цвета
        color_label = QLabel("Цвет:")
        color_label.setMaximumWidth(35)
        toolbar_layout.addWidget(color_label)

        self.color_combo = QComboBox()
        self.color_combo.addItems(["Красный", "Зеленый", "Синий", "Желтый", "Белый", "Черный"])
        self.color_combo.setCurrentText("Красный")
        self.color_combo.setMaximumWidth(80)
        self.color_combo.currentTextChanged.connect(self._on_color_changed)
        toolbar_layout.addWidget(self.color_combo)

        # Выбор толщины
        thickness_label = QLabel("Толщ:")
        thickness_label.setMaximumWidth(35)
        toolbar_layout.addWidget(thickness_label)

        self.thickness_combo = QComboBox()
        self.thickness_combo.addItems(["1", "2", "3", "4", "5"])
        self.thickness_combo.setCurrentText("2")
        self.thickness_combo.setMaximumWidth(50)
        self.thickness_combo.currentTextChanged.connect(self._on_thickness_changed)
        toolbar_layout.addWidget(self.thickness_combo)

        toolbar_layout.addStretch()

        # Кнопка очистки
        clear_btn = QPushButton("🗑️ Очистить")
        clear_btn.setMaximumWidth(80)
        clear_btn.setToolTip("Очистить все рисунки")
        clear_btn.clicked.connect(self._on_clear_drawing)
        toolbar_layout.addWidget(clear_btn)

        parent_layout.addLayout(toolbar_layout)

    def _on_drawing_tool_changed(self, button):
        """Обработка изменения инструмента рисования."""
        tool_id = self.drawing_tool_group.id(button)

        if tool_id == 0:  # Курсор
            self.drawing_overlay.set_tool(DrawingTool.NONE)
        elif tool_id == 1:  # Линия
            self.drawing_overlay.set_tool(DrawingTool.LINE)
            # Автопауза при выборе инструмента рисования
            if self.is_playing:
                self._on_play_pause_clicked()
        elif tool_id == 2:  # Прямоугольник
            self.drawing_overlay.set_tool(DrawingTool.RECTANGLE)
            # Автопауза при выборе инструмента рисования
            if self.is_playing:
                self._on_play_pause_clicked()
        elif tool_id == 3:  # Круг
            self.drawing_overlay.set_tool(DrawingTool.CIRCLE)
            # Автопауза при выборе инструмента рисования
            if self.is_playing:
                self._on_play_pause_clicked()
        elif tool_id == 4:  # Стрелка
            self.drawing_overlay.set_tool(DrawingTool.ARROW)
            # Автопауза при выборе инструмента рисования
            if self.is_playing:
                self._on_play_pause_clicked()

    def _on_color_changed(self):
        """Обработка изменения цвета."""
        color_name = self.color_combo.currentText()
        color_map = {
            "Красный": QColor("#FF0000"),
            "Зеленый": QColor("#00FF00"),
            "Синий": QColor("#0000FF"),
            "Желтый": QColor("#FFFF00"),
            "Белый": QColor("#FFFFFF"),
            "Черный": QColor("#000000")
        }
        color = color_map.get(color_name, QColor("#FF0000"))
        self.drawing_overlay.set_color(color)

    def _on_thickness_changed(self):
        """Обработка изменения толщины."""
        thickness = int(self.thickness_combo.currentText())
        self.drawing_overlay.set_thickness(thickness)

    def _on_clear_drawing(self):
        """Очистить все рисунки."""
        self.drawing_overlay.clear_drawing_with_confirmation(self)

    def _setup_shortcuts(self):
        """Настроить горячие клавиши для рисования."""
        # Ctrl+Z - отменить последнее действие
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self._on_undo_drawing)

        # Ctrl+X - очистить все с подтверждением
        clear_shortcut = QShortcut(QKeySequence("Ctrl+X"), self)
        clear_shortcut.activated.connect(self._on_clear_drawing_shortcut)

    def _on_undo_drawing(self):
        """Отменить последнее действие рисования (Ctrl+Z)."""
        if self.drawing_overlay.undo():
            # Можно добавить уведомление, но пока оставим без него
            pass

    def _on_clear_drawing_shortcut(self):
        """Очистить все рисунки через горячую клавишу (Ctrl+X)."""
        self.drawing_overlay.clear_drawing_with_confirmation(self)

    def _setup_ui(self):
        """Создать интерфейс."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # ===== ЛЕВАЯ ЧАСТЬ: ВИДЕОПЛЕЕР (70%) =====
        video_layout = QVBoxLayout()

        # Контейнер для видео с наложением рисования
        self.video_container = QWidget()
        self.video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_container.setMinimumSize(1, 1)
        self.video_container.setStyleSheet("background-color: black; border: 1px solid #555555;")

        # Видео
        self.video_label = QLabel(self.video_container)
        self.video_label.setGeometry(0, 0, 800, 450)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setToolTip("Preview video player")

        # Виджет для рисования поверх видео
        self.drawing_overlay = DrawingOverlay(self.video_container)
        self.drawing_overlay.setGeometry(0, 0, 800, 450)

        video_layout.addWidget(self.video_container)

        # Панель инструментов рисования
        self._setup_drawing_toolbar(video_layout)

        # Контролы видео
        controls_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setMaximumWidth(80)
        self.play_btn.setToolTip("Play/Pause preview (Space)")
        self.play_btn.clicked.connect(self._on_play_pause_clicked)
        controls_layout.addWidget(self.play_btn)
        
        # Ползунок
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setToolTip("Seek within current segment")
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        controls_layout.addWidget(self.progress_slider)
        
        # Время
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setMaximumWidth(120)
        self.time_label.setToolTip("Current time / Segment duration")
        controls_layout.addWidget(self.time_label)
        
        # Скорость
        speed_label = QLabel("Speed:")
        controls_layout.addWidget(speed_label)
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x", "3.0x", "4.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setMaximumWidth(80)
        self.speed_combo.setToolTip("Playback speed")
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        controls_layout.addWidget(self.speed_combo)
        
        controls_layout.addStretch()
        video_layout.addLayout(controls_layout)
        
        main_layout.addLayout(video_layout, 7)
        
        # ===== ПРАВАЯ ЧАСТЬ: СПИСОК ОТРЕЗКОВ (30%) =====
        list_layout = QVBoxLayout()

        # ===== КОМПАКТНЫЕ ФИЛЬТРЫ =====
        self._setup_filters(list_layout)

        # Список карточек событий
        self.markers_list = QListView()
        self.markers_list.setModel(self.markers_model)
        self.markers_list.setItemDelegate(self.markers_delegate)
        self.markers_list.setStyleSheet("""
            QListView {
                background-color: #2a2a2a;
                border: 1px solid #444444;
                outline: none;
                alternate-background-color: #2a2a2a;
            }
            QListView::item {
                border-bottom: 1px solid #333333;
                padding: 2px;
            }
            QListView::item:selected {
                background-color: #1a4d7a;
            }
        """)
        self.markers_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.markers_list.setSpacing(2)
        self.markers_list.setUniformItemSizes(True)  # Все элементы одинакового размера

        list_layout.addWidget(self.markers_list)

        main_layout.addLayout(list_layout, 3)

        central.setLayout(main_layout)



    def _update_marker_list(self):
        """Обновить список карточек событий с фильтрацией."""
        fps = self.controller.get_fps()

        # Установить FPS в делегате для форматирования времени
        self.markers_delegate.set_fps(fps)

        # Обновить модель с новыми данными и фильтрами
        self.markers_model.set_fps(fps)
        self.markers_model.set_markers(self.controller.markers)

        # Выделить текущую активную карточку
        self._update_active_card_highlight()

    def _on_card_play_requested(self, marker_idx: int):
        """Обработка запроса воспроизведения от карточки."""
        self.current_marker_idx = marker_idx
        marker = self.controller.markers[marker_idx]
        self.controller.seek_frame(marker.start_frame)
        self._display_current_frame()
        self._update_slider()
        self._update_active_card_highlight()

        # Автоматически начать воспроизведение
        if not self.is_playing:
            self._on_play_pause_clicked()

    def _on_card_edit_requested(self, marker_idx: int):
        """Обработка запроса редактирования от карточки."""
        # Поставить на паузу перед открытием редактора
        if self.is_playing:
            self._on_play_pause_clicked()

        # Использовать главное окно приложения для открытия редактора
        # Это обеспечит правильную интеграцию и навигацию
        main_window = None
        for widget in QApplication.topLevelWidgets():
            if hasattr(widget, 'open_segment_editor'):
                main_window = widget
                break

        if main_window:
            # Используем метод главного окна для открытия редактора
            main_window.open_segment_editor(marker_idx)
        else:
            # Fallback: создать окно напрямую (если главное окно не найдено)
            marker = self.controller.markers[marker_idx]

            # Создать список отфильтрованных маркеров для навигации
            filtered_markers = []
            for idx, m in enumerate(self.controller.markers):
                if self._passes_filters(m):
                    filtered_markers.append((idx, m))

            # Найти индекс текущего маркера в отфильтрованном списке
            current_filtered_idx = None
            for i, (orig_idx, m) in enumerate(filtered_markers):
                if orig_idx == marker_idx:
                    current_filtered_idx = i
                    break

            # Создать новое окно редактирования
            from .instance_edit_window import InstanceEditWindow
            self.instance_edit_window = InstanceEditWindow(
                marker, self.controller, filtered_markers, current_filtered_idx, self
            )
            self.instance_edit_window.marker_updated.connect(self._on_instance_updated_externally)
            self.instance_edit_window.show()

    def _on_card_delete_requested(self, marker_idx: int):
        """Обработка запроса удаления от карточки."""
        self.controller.delete_marker(marker_idx)
        self._update_marker_list()

    def _update_active_card_highlight(self):
        """Выделить активную карточку (которая воспроизводится сейчас)."""
        # Найти строку в модели для текущего маркера
        row = self.markers_model.find_row_by_marker_idx(self.current_marker_idx)

        if row >= 0:
            # Выделить элемент в QListView
            index = self.markers_model.index(row, 0)
            self.markers_list.setCurrentIndex(index)
            # Автоскролл к выделенному элементу
            self.markers_list.scrollTo(index)

    def _passes_filters(self, marker):
        """Проверить, проходит ли маркер через текущие фильтры."""
        # Фильтр по типу события
        if self.filter_event_types and marker.event_name not in self.filter_event_types:
            return False

        # Фильтр по заметкам
        if self.filter_has_notes and not marker.note.strip():
            return False

        # Фильтр по поиску в заметках
        if self.filter_notes_search and self.filter_notes_search not in marker.note.lower():
            return False

        return True



    def _on_play_pause_clicked(self):
        """Кнопка Play/Pause."""
        if not self.controller.markers:
            return

        if self.is_playing:
            self.playback_timer.stop()
            self.is_playing = False
            self.play_btn.setText("▶ Play")
        else:
            # Всегда брать актуальную скорость перед запуском воспроизведения
            fps = self.controller.get_fps()
            speed = self.controller.get_playback_speed()
            if fps > 0:
                self.frame_time_ms = int(1000 / (fps * speed))

            self.is_playing = True
            self.play_btn.setText("⏸ Pause")
            self.playback_timer.start(self.frame_time_ms)

    def _on_playback_tick(self):
        """Таймер воспроизведения с логикой плейлиста."""
        if not self.controller.markers:
            self.is_playing = False
            self.play_btn.setText("▶ Play")
            self.playback_timer.stop()
            return

        # Получить текущий маркер
        marker = self.controller.markers[self.current_marker_idx]
        current_frame = self.controller.processor.get_current_frame_idx()

        # 1. Если достигли конца текущего отрезка
        if current_frame >= marker.end_frame:
            # ---> ЛОГИКА АВТОПЕРЕХОДА <---

            # Найти следующий маркер в отфильтрованном списке
            next_marker_idx = self._find_next_filtered_marker(self.current_marker_idx)

            if next_marker_idx is not None:
                # Переключаемся на следующий маркер
                self.current_marker_idx = next_marker_idx
                next_marker = self.controller.markers[next_marker_idx]

                # Мгновенный переход (без паузы между клипами)
                self.controller.seek_frame(next_marker.start_frame)
                self._update_active_card_highlight()

            else:
                # Конец плейлиста -> Стоп
                self.is_playing = False
                self.play_btn.setText("▶ Play")
                self.playback_timer.stop()
            return

        # 2. Обычное воспроизведение
        self.controller.processor.advance_frame()
        self._display_current_frame()
        self._update_slider()

    def _find_next_filtered_marker(self, current_idx: int) -> Optional[int]:
        """Найти следующий маркер, соответствующий фильтрам."""
        for idx in range(current_idx + 1, len(self.controller.markers)):
            marker = self.controller.markers[idx]
            if self._passes_filters(marker):
                return idx
        return None

    def _go_to_next_marker(self):
        """Перейти на следующий отрезок (с фильтрацией)."""
        next_marker_idx = self._find_next_filtered_marker(self.current_marker_idx)

        if next_marker_idx is not None:
            self.current_marker_idx = next_marker_idx
            marker = self.controller.markers[next_marker_idx]
            self.controller.seek_frame(marker.start_frame)
            self._display_current_frame()
            self._update_slider()
            self._update_active_card_highlight()
            return

        # Конец списка
        self.is_playing = False
        self.play_btn.setText("▶ Play")
        self.playback_timer.stop()

    def _on_slider_moved(self):
        """Движение ползунка."""
        frame_idx = self.progress_slider.value()
        self.controller.seek_frame(frame_idx)
        self._display_current_frame()
        self._update_slider()



    def _display_current_frame(self):
        """Отобразить текущий кадр."""
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
        scaled_pixmap = pixmap.scaled(self.video_container.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)

        # Центрировать изображение в контейнере
        container_width = self.video_container.width()
        container_height = self.video_container.height()
        pixmap_width = scaled_pixmap.width()
        pixmap_height = scaled_pixmap.height()

        x = (container_width - pixmap_width) // 2
        y = (container_height - pixmap_height) // 2

        self.video_label.setGeometry(x, y, pixmap_width, pixmap_height)
        self.video_label.setPixmap(scaled_pixmap)

        # Обновить размер drawing overlay
        self.drawing_overlay.setGeometry(x, y, pixmap_width, pixmap_height)

    def _update_slider(self):
        """Обновить ползунок и время."""
        if not self.controller.markers or self.current_marker_idx >= len(self.controller.markers):
            return
        
        marker = self.controller.markers[self.current_marker_idx]
        current_frame = self.controller.processor.get_current_frame_idx()
        fps = self.controller.get_fps()
        
        # Ползунок
        self.progress_slider.blockSignals(True)
        self.progress_slider.setMinimum(marker.start_frame)
        self.progress_slider.setMaximum(marker.end_frame)
        self.progress_slider.setValue(current_frame)
        self.progress_slider.blockSignals(False)
        
        # Время
        if fps > 0:
            current_time = current_frame / fps
            end_time = marker.end_frame / fps
            self.time_label.setText(f"{self._format_time(current_time)} / {self._format_time(end_time)}")

    def _on_speed_changed(self):
        """Обработка изменения скорости воспроизведения."""
        speed_text = self.speed_combo.currentText()
        speed = float(speed_text.replace('x', ''))
        self.controller.set_playback_speed(speed)

        # Обновить frame_time_ms для локального таймера
        fps = self.controller.get_fps()
        if fps > 0:
            self.frame_time_ms = int(1000 / (fps * speed))

        # Если воспроизведение активно, перезапустить таймер с новой скоростью
        if self.is_playing:
            self.playback_timer.start(self.frame_time_ms)

    def _update_speed_combo(self):
        """Обновить комбо-бокс скорости в соответствии с текущей скоростью контроллера."""
        current_speed = self.controller.get_playback_speed()
        speed_text = f"{current_speed:.2f}x"

        # Найти наиболее близкий вариант в списке
        items = [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]
        if speed_text in items:
            self.speed_combo.setCurrentText(speed_text)
        else:
            # Если точного совпадения нет, выбрать наиболее близкий
            closest_item = min(items, key=lambda x: abs(float(x.replace('x', '')) - current_speed))
            self.speed_combo.setCurrentText(closest_item)

    def resizeEvent(self, event):
        """Обработка изменения размера окна."""
        super().resizeEvent(event)
        # Обновить отображение кадра при изменении размера
        if hasattr(self, 'controller') and self.controller.processor:
            self._display_current_frame()

    def _format_time(self, seconds: float) -> str:
        """Форматировать время MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    def _update_inspector_event_types(self):
        """Заполнить комбо-бокс типов событий в инспекторе."""
        self.event_type_combo.blockSignals(True)
        self.event_type_combo.clear()

        # Добавить все доступные типы событий
        from ..utils.custom_events import get_custom_event_manager
        event_manager = get_custom_event_manager()
        events = event_manager.get_all_events()
        for event in events:
            localized_name = event.get_localized_name()
            self.event_type_combo.addItem(localized_name, event.name)

        self.event_type_combo.blockSignals(False)

    def _on_marker_selection_changed(self):
        """Обработка изменения выбора строки в таблице - обновить инспектор."""
        marker_idx, marker = self._get_selected_marker()
        if marker is None:
            # Очистить поля инспектора
            self.event_type_combo.blockSignals(True)
            self.event_type_combo.setCurrentIndex(-1)
            self.event_type_combo.blockSignals(False)
            self.start_time_edit.clear()
            self.end_time_edit.clear()
            self.notes_edit.clear()
            return

        fps = self.controller.get_fps()
        if fps <= 0:
            return

        # Заполнить поля данными маркера
        self.event_type_combo.blockSignals(True)
        # Найти индекс текущего типа события
        for i in range(self.event_type_combo.count()):
            if self.event_type_combo.itemData(i) == marker.event_name:
                self.event_type_combo.setCurrentIndex(i)
                break
        self.event_type_combo.blockSignals(False)

        # Время начала и конца
        start_time = self._format_time(marker.start_frame / fps)
        end_time = self._format_time(marker.end_frame / fps)
        self.start_time_edit.setText(start_time)
        self.end_time_edit.setText(end_time)

        # Заметки
        self.notes_edit.setText(marker.note)

    def _on_inspector_event_type_changed(self):
        """Обработка изменения типа события в инспекторе."""
        marker_idx, marker = self._get_selected_marker()
        if marker is None:
            return

        current_data = self.event_type_combo.currentData()
        if current_data:
            marker.event_name = current_data
            self.controller.markers_changed.emit()
            self._update_marker_list()

    def _on_inspector_start_time_changed(self):
        """Обработка изменения времени начала в инспекторе."""
        marker_idx, marker = self._get_selected_marker()
        if marker is None:
            return

        fps = self.controller.get_fps()
        if fps <= 0:
            return

        # Парсинг времени из формата MM:SS
        time_text = self.start_time_edit.text().strip()
        try:
            if ":" in time_text:
                minutes, seconds = map(int, time_text.split(":"))
                total_seconds = minutes * 60 + seconds
            else:
                total_seconds = float(time_text)

            new_start_frame = int(total_seconds * fps)

            # Валидация: начало не может быть больше конца
            if new_start_frame > marker.end_frame:
                # Автоматически сдвинуть конец
                marker.end_frame = max(marker.end_frame, new_start_frame + int(fps))

            marker.start_frame = max(0, new_start_frame)
            self.controller.markers_changed.emit()
            self._update_marker_list()
            # Обновить поле в инспекторе
            self._on_marker_selection_changed()

        except (ValueError, IndexError):
            # Восстановить предыдущее значение
            self._on_marker_selection_changed()

    def _on_inspector_end_time_changed(self):
        """Обработка изменения времени конца в инспекторе."""
        marker_idx, marker = self._get_selected_marker()
        if marker is None:
            return

        fps = self.controller.get_fps()
        if fps <= 0:
            return

        # Парсинг времени из формата MM:SS
        time_text = self.end_time_edit.text().strip()
        try:
            if ":" in time_text:
                minutes, seconds = map(int, time_text.split(":"))
                total_seconds = minutes * 60 + seconds
            else:
                total_seconds = float(time_text)

            new_end_frame = int(total_seconds * fps)
            total_frames = self.controller.get_total_frames()

            # Валидация: конец не может быть меньше начала
            if new_end_frame < marker.start_frame:
                # Автоматически сдвинуть начало
                marker.start_frame = max(0, new_end_frame - int(fps))

            marker.end_frame = min(total_frames - 1, new_end_frame)
            self.controller.markers_changed.emit()
            self._update_marker_list()
            # Обновить поле в инспекторе
            self._on_marker_selection_changed()

        except (ValueError, IndexError):
            # Восстановить предыдущее значение
            self._on_marker_selection_changed()

    def _on_inspector_notes_changed(self):
        """Обработка изменения заметок в инспекторе."""
        marker_idx, marker = self._get_selected_marker()
        if marker is None:
            return

        marker.note = self.notes_edit.text().strip()
        self.controller.markers_changed.emit()
        self._update_marker_list()
