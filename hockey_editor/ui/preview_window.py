"""
Preview Window - просмотр и воспроизведение отрезков (PySide6).
Немодальное окно с видеоплеером и списком отрезков.
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap, QImage, QFont, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QListWidget, QListWidgetItem, QCheckBox, QComboBox, QGroupBox,
    QSpinBox, QLineEdit, QButtonGroup
)
import cv2
import numpy as np
from typing import Optional
from ..models.marker import Marker, EventType
from .drawing_overlay import DrawingOverlay, DrawingTool


class PreviewWindow(QMainWindow):
    """
    Окно предпросмотра отрезков.
    Содержит видеоплеер и список отрезков с фильтрацией.
    """
    
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Preview - Segments")
        self.setGeometry(100, 100, 1400, 800)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)  # Немодальное окно
        self.setStyleSheet(self._get_dark_stylesheet())
        
        # Параметры воспроизведения
        self.current_marker_idx = 0
        self.is_playing = False
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)
        self.frame_time_ms = 33  # ~30 FPS

        # Инициализация фильтров
        self._init_filters()

        self._setup_ui()
        self._setup_shortcuts()
        self._update_speed_combo()
        self._update_marker_list()

        # Подключить сигнал изменения событий
        from ..utils.custom_events import get_custom_event_manager
        self.event_manager = get_custom_event_manager()
        self.event_manager.events_changed.connect(self._on_events_changed)

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
        elif tool_id == 2:  # Прямоугольник
            self.drawing_overlay.set_tool(DrawingTool.RECTANGLE)
        elif tool_id == 3:  # Круг
            self.drawing_overlay.set_tool(DrawingTool.CIRCLE)
        elif tool_id == 4:  # Стрелка
            self.drawing_overlay.set_tool(DrawingTool.ARROW)

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
        self.video_container.setMinimumSize(800, 450)
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
        
        # Список отрезков
        self.markers_list = QListWidget()
        self.markers_list.setToolTip("Click to preview segment")
        self.markers_list.itemClicked.connect(self._on_marker_selected)
        list_layout.addWidget(self.markers_list)
        
        # Кнопки
        btn_layout = QHBoxLayout()
        
        edit_btn = QPushButton("✎ Edit")
        edit_btn.setToolTip("Edit selected segment")
        edit_btn.clicked.connect(self._on_edit_marker)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.setToolTip("Delete selected segment")
        delete_btn.clicked.connect(self._on_delete_marker)
        btn_layout.addWidget(delete_btn)
        
        list_layout.addLayout(btn_layout)
        
        main_layout.addLayout(list_layout, 3)
        
        central.setLayout(main_layout)

    def _update_marker_list(self):
        """Обновить список отрезков с фильтрацией."""
        self.markers_list.clear()

        fps = self.controller.get_fps()

        for idx, marker in enumerate(self.controller.markers):
            # Применить фильтры
            if not self._passes_filters(marker):
                continue

            start_time = self._format_time(marker.start_frame / fps if fps > 0 else 0)
            end_time = self._format_time(marker.end_frame / fps if fps > 0 else 0)
            duration_frames = marker.end_frame - marker.start_frame
            duration_sec = duration_frames / fps if fps > 0 else 0

            text = f"{idx+1}. {marker.event_name} ({start_time}–{end_time}) [{duration_sec:.1f}s]"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, idx)  # Сохранить оригинальный индекс

            # Получить цвет события из CustomEventManager
            from ..utils.custom_events import get_custom_event_manager
            event_manager = get_custom_event_manager()
            event = event_manager.get_event(marker.event_name)
            if event:
                item.setForeground(event.get_qcolor())
            else:
                item.setForeground(QColor(150, 150, 150))  # Серый по умолчанию

            self.markers_list.addItem(item)

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

    def _on_marker_selected(self, item: QListWidgetItem):
        """Клик на отрезок = воспроизведение с начала."""
        marker_idx = item.data(Qt.ItemDataRole.UserRole)
        self.current_marker_idx = marker_idx
        
        marker = self.controller.markers[marker_idx]
        self.controller.seek_frame(marker.start_frame)
        self._display_current_frame()
        self._update_slider()
        
        # Автоматически начать воспроизведение
        if not self.is_playing:
            self._on_play_pause_clicked()

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
        """Таймер воспроизведения."""
        if not self.controller.markers or self.current_marker_idx >= len(self.controller.markers):
            self.is_playing = False
            self.play_btn.setText("▶ Play")
            self.playback_timer.stop()
            return
        
        marker = self.controller.markers[self.current_marker_idx]
        current_frame = self.controller.processor.get_current_frame_idx()
        
        # Если достигли конца отрезка
        if current_frame >= marker.end_frame:
            # Переместиться на следующий отрезок (с фильтрацией)
            self._go_to_next_marker()
            return
        
        # Воспроизвести следующий кадр
        self.controller.processor.advance_frame()
        self._display_current_frame()
        self._update_slider()

    def _go_to_next_marker(self):
        """Перейти на следующий отрезок (с фильтрацией)."""
        # Найти следующий отрезок, соответствующий фильтру
        for idx in range(self.current_marker_idx + 1, len(self.controller.markers)):
            marker = self.controller.markers[idx]

            if self._passes_filters(marker):
                self.current_marker_idx = idx
                self.controller.seek_frame(marker.start_frame)
                self.markers_list.setCurrentRow(idx)
                self._display_current_frame()
                self._update_slider()
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

    def _on_edit_marker(self):
        """Отредактировать выбранный отрезок."""
        current_idx = self.markers_list.currentRow()
        if current_idx < 0:
            return

        marker_idx = self.markers_list.item(current_idx).data(Qt.ItemDataRole.UserRole)
        from .edit_segment_dialog import EditSegmentDialog
        marker = self.controller.markers[marker_idx]
        dialog = EditSegmentDialog(marker, self.controller.get_fps(), self.controller, self)
        if dialog.exec():
            self.controller.markers[marker_idx] = dialog.get_marker()
            self.controller.markers_changed.emit()
        self._update_marker_list()

    def _on_delete_marker(self):
        """Удалить выбранный отрезок."""
        current_idx = self.markers_list.currentRow()
        if current_idx < 0:
            return
        
        marker_idx = self.markers_list.item(current_idx).data(Qt.ItemDataRole.UserRole)
        self.controller.delete_marker(marker_idx)
        self._update_marker_list()

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

    def _get_dark_stylesheet(self) -> str:
        """Тёмный стиль."""
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
        QPushButton:checked {
            background-color: #ffcc00;
            color: #000000;
            border: 2px solid #ffaa00;
        }
        QPushButton:checked:hover {
            background-color: #ffdd44;
        }
        QSlider::groove:horizontal {
            background: #333333;
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: #ffcc00;
            width: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }
        QListWidget {
            background-color: #2a2a2a;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QLabel, QCheckBox {
            color: #ffffff;
        }
        QComboBox {
            background-color: #333333;
            color: #ffffff;
            border: 1px solid #555555;
        }
        QGroupBox {
            border: 1px solid #555555;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
        }
        QLineEdit {
            background-color: #333333;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 3px;
            border-radius: 3px;
        }
        """
