"""
Main Window - Primary application window for Hockey Editor.

Recreated from hockey_editor_OLD/hockey_editor/ui/main_window.py
to maintain identical visual appearance, layout, functionality, and behavior.
Adapted to new MVC architecture with signals/slots and separated controllers.
"""

from typing import Optional, List, Set
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSplitter,
    QMenuBar, QMenu, QStatusBar, QComboBox, QCheckBox, QPushButton,
    QMessageBox, QFileDialog, QSpinBox, QListWidget, QListWidgetItem
)
from PySide6.QtGui import QPixmap, QImage, QKeySequence, QKeyEvent, QShortcut, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt, Signal, QMimeData
import cv2
import numpy as np
from pathlib import Path

# Импорты для работы из корня проекта (main.py добавляет src в sys.path)
from views.widgets.player_controls import PlayerControls
from views.widgets.segment_list import SegmentListWidget
# Use timeline widget from new structure
from views.widgets.timeline import TimelineWidget
from views.styles import get_application_stylesheet
# Импортируем EventShortcutListWidget
from views.widgets.event_shortcut_list_widget import EventShortcutListWidget

# Import utilities from old version, adapted to new structure
from services.serialization.settings_manager import get_settings_manager
from services.events.custom_event_manager import get_custom_event_manager

class MainWindow(QMainWindow):
    """Главное окно приложения - точная копия из hockey_editor_OLD/ui/main_window.py."""

    # Signals for menu actions (adapted from old version)
    open_video_triggered = Signal()
    save_project_triggered = Signal()
    load_project_triggered = Signal()
    new_project_triggered = Signal()
    open_settings_triggered = Signal()
    export_triggered = Signal()
    open_preview_triggered = Signal()

    # Signal for keyboard shortcuts
    key_pressed = Signal(str)  # Pressed key (e.g., 'G', 'H')

    # Additional signals for old functionality
    undo_triggered = Signal()
    redo_triggered = Signal()
    cancel_recording_triggered = Signal()
    play_pause_triggered = Signal()
    speed_changed = Signal(float)
    seek_frame_triggered = Signal(int)
    skip_seconds_triggered = Signal(int)
    fullscreen_triggered = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # Initialize managers from old version
        self.settings_manager = get_settings_manager()
        self.event_manager = get_custom_event_manager()
        self.event_manager.setParent(self)  # Ensure proper Qt object ownership
        # Shortcut manager removed - using ShortcutController instead
        self.shortcut_manager = None

        # Autosave from old version (TODO: integrate)
        # from hockey_editor.utils.autosave import AutosaveManager
        # Note: AutosaveManager needs controller, will be initialized later via set_controller

        self.setWindowTitle("Хоккейный Редактор")
        self.setGeometry(0, 0, 1800, 1000)

        # Поддержка drag-drop для видео
        self.setAcceptDrops(True)

        # Ensure main window always gets keyboard events
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_AlwaysShowToolTips)

        # Инициализация фильтров (from old version)
        self._init_filters()

        # Apply application stylesheet
        self.setStyleSheet(get_application_stylesheet())

        # Create menu bar (adapted from old version)
        self._create_menu()

        # Setup UI (adapted from old version)
        self.setup_ui()

        # Connect signals (will be called after controller is set)
        # self.connect_signals()

        # Setup shortcuts (adapted from old version)
        # Shortcuts are now handled by ShortcutController
        # self._setup_shortcuts()

    def _init_filters(self):
        """Инициализация состояния фильтров (from old version)."""
        self.filter_event_types = set()  # Множество выбранных типов событий
        self.filter_has_notes = False    # Фильтр по наличию заметок

    def _setup_filters(self, parent_layout):
        """Создать элементы управления фильтрами (from old version)."""
        # Контейнер для фильтров
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(5)

        # Фильтр по типу события
        event_filter_label = QLabel("Тип:")
        event_filter_label.setMaximumWidth(30)
        filters_layout.addWidget(event_filter_label)

        self.event_filter_combo = QComboBox()
        self.event_filter_combo.setToolTip("Фильтр по типу события")
        self.event_filter_combo.setMaximumWidth(120)
        self.event_filter_combo.currentTextChanged.connect(self._on_event_filter_changed)
        filters_layout.addWidget(self.event_filter_combo)

        # Чекбокс для фильтра заметок
        self.notes_filter_checkbox = QCheckBox("Заметки")
        self.notes_filter_checkbox.setToolTip("Показывать только отрезки с заметками")
        self.notes_filter_checkbox.stateChanged.connect(self._on_notes_filter_changed)
        filters_layout.addWidget(self.notes_filter_checkbox)

        # Кнопка сброса фильтров
        reset_btn = QPushButton("Сброс")
        reset_btn.setMaximumWidth(80)
        reset_btn.setToolTip("Сбросить все фильтры")
        reset_btn.clicked.connect(self._reset_filters)
        filters_layout.addWidget(reset_btn)

        filters_layout.addStretch()

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
        events = self.event_manager.get_all_events()
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

        self._on_markers_changed()

    def _on_notes_filter_changed(self):
        """Обработка изменения фильтра заметок."""
        self.filter_has_notes = self.notes_filter_checkbox.isChecked()
        self._on_markers_changed()

    def _reset_filters(self):
        """Сбросить все фильтры."""
        self.event_filter_combo.blockSignals(True)
        self.event_filter_combo.setCurrentIndex(0)  # "Все"
        self.event_filter_combo.blockSignals(False)

        self.notes_filter_checkbox.setChecked(False)

        self.filter_event_types.clear()
        self.filter_has_notes = False

        self._on_markers_changed()

    def _create_menu(self):
        """Создать меню приложения (adapted from old version)."""
        self.menubar = self.menuBar()
        self.menubar.clear()  # Очистка на всякий случай

        # === File Menu ===
        self.file_menu = self.menubar.addMenu("Файл")

        self.action_new = self.file_menu.addAction("Новый проект")
        self.action_new.setShortcut("Ctrl+N")
        self.action_new.triggered.connect(self._on_new_project)

        self.action_open = self.file_menu.addAction("Открыть проект")
        self.action_open.setShortcut("Ctrl+O")
        self.action_open.triggered.connect(self._on_open_project)

        self.action_open_video = self.file_menu.addAction("Открыть видео")
        self.action_open_video.triggered.connect(self._on_open_video)

        self.action_save = self.file_menu.addAction("Сохранить проект")
        self.action_save.setShortcut("Ctrl+S")
        self.action_save.triggered.connect(self._on_save_project)

        self.action_save_as = self.file_menu.addAction("Сохранить проект как...")
        self.action_save_as.setShortcut("Ctrl+Shift+S")
        self.action_save_as.triggered.connect(self._on_save_project_as)

        self.file_menu.addSeparator()

        # Recent Projects
        self.recent_menu = self.file_menu.addMenu("Недавние проекты")
        self._update_recent_menu()

        self.file_menu.addSeparator()

        self.action_exit = self.file_menu.addAction("Выход")
        self.action_exit.triggered.connect(self.close)

        # === Action buttons in menu bar ===
        self.action_preview = self.menubar.addAction("Предпросмотр")
        self.action_preview.setShortcut("Ctrl+P")
        self.action_preview.triggered.connect(self._on_preview_clicked)

        self.action_settings = self.menubar.addAction("Настройки")
        self.action_settings.setShortcut("Ctrl+,")
        self.action_settings.triggered.connect(self._on_settings_clicked)

        self.action_export = self.menubar.addAction("Экспорт")
        self.action_export.setShortcut("Ctrl+E")
        self.action_export.triggered.connect(self._on_export_clicked)

        # === Help Menu ===
        self.help_menu = self.menubar.addMenu("Справка")

        self.action_about = self.help_menu.addAction("О программе")
        self.action_about.triggered.connect(self._on_about)

    def _update_recent_menu(self):
        """Обновить меню недавних проектов (adapted from old version)."""
        self.recent_menu.clear()

        # TODO: Get recent projects from controller
        recent_projects = []  # self.controller.get_recent_projects()
        if not recent_projects:
            self.recent_menu.addAction("(No recent projects)")
            return

        for path in recent_projects:
            action = self.recent_menu.addAction(Path(path).name)
            action.triggered.connect(lambda checked, p=path: self._on_recent_project(p))

    def _on_recent_project(self, path: str):
        """Открыть недавний проект (adapted from old version)."""
        # TODO: Implement via controller
        pass

    def setup_ui(self):
        """Создать UI (adapted from old version)."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)

        # ===== ВЕРХНЯЯ ЧАСТЬ (видео + список справа) =====
        # Используем QSplitter для возможности изменения пропорций
        self.top_splitter = QSplitter(Qt.Horizontal)
        self.top_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #333333;
                border: 1px solid #555555;
            }
            QSplitter::handle:hover {
                background-color: #444444;
            }
        """)

        # Видео контейнер с интегрированными элементами управления
        video_container = QWidget()
        video_container_layout = QVBoxLayout(video_container)
        video_container_layout.setContentsMargins(0, 0, 0, 0)
        video_container_layout.setSpacing(0)  # Убираем промежутки между элементами

        # Видео виджет
        from views.widgets.scalable_video_label import ScalableVideoLabel
        self.video_label = ScalableVideoLabel()
        self.video_label.setMinimumSize(320, 180)
        # Убрано ограничение максимального размера для занятия всей доступной высоты верхней половины экрана
        self.video_label.setStyleSheet("background-color: black;")  # Рамка убрана, фон черный
        video_container_layout.addWidget(self.video_label, 1)  # stretch factor 1 для занятия основного пространства

        # Профессиональная панель управления (интегрирована в нижнюю часть видео-фрейма)
        self.player_controls = PlayerControls()
        # Signals will be connected later via set_controller
        video_container_layout.addWidget(self.player_controls, 0, Qt.AlignBottom)  # Приклеена к нижней части

        self.top_splitter.addWidget(video_container)

        # Список отрезков
        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)  # Убираем отступы для плотного прилегания
        list_layout.addWidget(QLabel("Отрезки:"))

        # ===== ФИЛЬТРЫ =====
        self._setup_filters(list_layout)

        # Новый виджет списка сегментов
        self.segment_list_widget = SegmentListWidget()
        # Signals will be connected later
        list_layout.addWidget(self.segment_list_widget)

        self.top_splitter.addWidget(list_container)

        # Установить начальные пропорции (60:40)
        self.top_splitter.setSizes([600, 400])

        # ===== ОСНОВНОЙ VERTICAL SPLITTER =====
        # Создаем вертикальный splitter для разделения верхней части (видео+список) и нижней (таймлайн)
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #333333;
                border: 1px solid #555555;
            }
            QSplitter::handle:hover {
                background-color: #444444;
            }
        """)

        # Верхняя часть - видео и список отрезков
        self.main_splitter.addWidget(self.top_splitter)

        # Нижняя часть - таймлайн
        timeline_container = QWidget()
        timeline_layout = QVBoxLayout(timeline_container)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.addWidget(QLabel("Таймлайн:"))

        # Timeline widget (will be set via set_timeline_controller)
        # self.timeline_widget = TimelineWidget()  # Will be set later
        # timeline_layout.addWidget(self.timeline_widget)

        timeline_layout.addWidget(timeline_container)

        # Установить начальные пропорции (70:30)
        self.main_splitter.setSizes([630, 270])

        main_layout.addWidget(self.main_splitter)

        # ===== НИЖНЯЯ ЧАСТЬ: СПИСОК СОБЫТИЙ И СТАТУС-БАР =====
        bottom_layout = QHBoxLayout()

        # Виджет списка событий с горячими клавишами
        self.event_shortcut_list_widget = EventShortcutListWidget()
        # Signals will be connected later
        bottom_layout.addWidget(self.event_shortcut_list_widget)

        bottom_layout.addStretch()

        # Статус-бар с фиксированной высотой
        self.status_label = QLabel("Готов")
        self.status_label.setStyleSheet("color: #ffcc00;")
        self.status_label.setMinimumWidth(400)
        self.status_label.setFixedHeight(22)  # Фиксированная высота 20-24px
        bottom_layout.addWidget(self.status_label)

        # Индикатор режима записи
        self.mode_indicator = QLabel("Режим: Фиксированная длина")
        self.mode_indicator.setStyleSheet("color: #00ccff; font-weight: bold;")
        self.mode_indicator.setMinimumWidth(250)
        self.mode_indicator.setFixedHeight(22)
        bottom_layout.addWidget(self.mode_indicator)

        main_layout.addLayout(bottom_layout)

        central.setLayout(main_layout)


    # Menu action handlers
    def _on_new_project(self) -> None:
        """Handle new project action."""
        self.new_project_triggered.emit()

    def _on_open_video(self) -> None:
        """Handle open video action."""
        self.open_video_triggered.emit()

    def _on_load_project(self) -> None:
        """Handle load project action."""
        self.load_project_triggered.emit()

    def _on_save_project(self) -> None:
        """Handle save project action."""
        self.save_project_triggered.emit()

    def _on_save_project_as(self) -> None:
        """Handle save project as action."""
        # For now, emit the same signal as save
        self.save_project_triggered.emit()

    def _on_open_preferences(self) -> None:
        """Handle open preferences action."""
        self.open_settings_triggered.emit()

    def _on_export(self) -> None:
        """Handle export action."""
        self.export_triggered.emit()

    def _on_open_preview(self) -> None:
        """Handle open preview window action."""
        self.open_preview_triggered.emit()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events for shortcuts."""
        # Ignore auto-repeats
        if event.isAutoRepeat():
            return

        key = event.key()
        print(f"DEBUG: MainWindow keyPressEvent - key: {key}, text: {event.text()}")

        # Handle letter keys (A-Z)
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            key_char = chr(key).upper()
            print(f"DEBUG: Emitting key_pressed signal for key: {key_char}")
            self.key_pressed.emit(key_char)
            return

        # Handle other keys if needed
        super().keyPressEvent(event)

    # Public interface methods
    def set_video_image(self, pixmap: QPixmap) -> None:
        """Set the video display image."""
        self.video_label.setPixmap(pixmap)

    def set_window_title(self, title: str) -> None:
        """Set the window title with project name."""
        if title:
            self.setWindowTitle(f"Hockey Editor - {title}")
        else:
            self.setWindowTitle("Hockey Editor")

    def update_status_bar(self, message: str) -> None:
        """Update the status bar message."""
        self.status_bar.showMessage(message)

    def get_player_controls(self) -> PlayerControls:
        """Get the player controls widget."""
        return self.player_controls

    def get_segment_list_widget(self) -> SegmentListWidget:
        """Get the segment list widget."""
        return self.segment_list_widget

    # ===== MVC Integration Methods =====

    def set_controller(self, controller) -> None:
        """Set the main controller and connect signals (adapted from old version)."""
        self.controller = controller

        # Initialize autosave (TODO: integrate from old version)
        # self.autosave_manager = AutosaveManager(controller)
        # self.autosave_manager.autosave_completed.connect(self._on_autosave_completed)
        self.autosave_manager = None

        # Connect signals
        self.connect_signals()

        # Start autosave (TODO)
        # if self.autosave_manager:
        #     self.autosave_manager.start()

    def set_timeline_controller(self, timeline_controller) -> None:
        """Set the timeline controller and widget."""
        # Create timeline widget with controller
        self.timeline_widget = TimelineWidget()  # Adapted for new architecture

        # Find the timeline container and add the widget
        # The timeline_container is the second widget in main_splitter
        timeline_container = self.main_splitter.widget(1)
        if timeline_container and hasattr(timeline_container, 'layout'):
            timeline_layout = timeline_container.layout()
            timeline_layout.addWidget(self.timeline_widget)

    def connect_signals(self):
        """Подключить сигналы контроллера (adapted from old version)."""
        # Playback signals
        self.controller.playback_time_changed.connect(self._on_playback_time_changed)
        self.controller.markers_changed.connect(self._on_markers_changed)
        self.controller.recording_status_changed.connect(self._on_recording_status_changed)
        self.controller.timeline_update.connect(self._on_timeline_update)
        self.controller.frame_ready.connect(self._on_frame_ready)

        # Events
        self.event_manager.events_changed.connect(self._on_events_changed)
        self.event_manager.events_changed.connect(self._on_events_changed_timeline)

        # UI signals
        self.player_controls.playClicked.connect(self._on_play_pause_clicked)
        self.player_controls.speedStepChanged.connect(self._on_speed_step_changed)
        self.player_controls.skipSeconds.connect(self._on_skip_seconds)
        self.player_controls.speedChanged.connect(self._on_speed_changed)
        self.player_controls.fullscreenClicked.connect(self._on_fullscreen_clicked)

        self.event_shortcut_list_widget.event_selected.connect(self._on_event_btn_clicked)
        self.segment_list_widget.segment_edit_requested.connect(self._on_segment_edit_requested)
        self.segment_list_widget.segment_delete_requested.connect(self._on_segment_delete_requested)
        self.segment_list_widget.segment_jump_requested.connect(self._on_segment_jump_requested)

        # Shortcut signals
        if hasattr(self, 'shortcut_controller'):
            self.shortcut_controller.shortcut_pressed.connect(self._on_shortcut_pressed)

    # ===== Event Handlers (adapted from old version) =====

    def _on_play_pause_clicked(self):
        """Кнопка Play/Pause - переключение."""
        self.play_pause_triggered.emit()

    def _on_speed_step_changed(self, step: int):
        """Изменение скорости на шаг (±1)."""
        self.speed_changed.emit(self.controller.get_playback_speed() + step * 0.25)  # Simplified

    def _on_skip_seconds(self, seconds: int):
        """Перемотка на секунды."""
        self.skip_seconds_triggered.emit(seconds)

    def _on_speed_changed(self, speed: float):
        """Изменение скорости."""
        self.speed_changed.emit(speed)

    def _on_fullscreen_clicked(self):
        """Переключение полноэкранного режима."""
        self.fullscreen_triggered.emit()

    def _on_event_btn_clicked(self, event_name: str):
        """Нажатие кнопки события."""
        # Передаем событие в контроллер через сигнал
        print(f"DEBUG: Event button clicked - event_name: {event_name}")
        self.key_pressed.emit(event_name.upper())

    def _on_segment_edit_requested(self, marker_idx: int):
        """Обработка запроса редактирования сегмента."""
        # Вызываем метод контроллера для открытия редактора сегмента
        if hasattr(self, '_timeline_controller'):
            self._timeline_controller.edit_marker_requested(marker_idx)

    def _on_segment_delete_requested(self, marker_idx: int):
        """Обработка запроса удаления сегмента."""
        # Вызываем метод контроллера для удаления сегмента
        if hasattr(self, '_timeline_controller'):
            self._timeline_controller.delete_marker(marker_idx)

    def _on_segment_jump_requested(self, marker_idx: int):
        """Обработка запроса перехода к моменту времени сегмента."""
        # Вызываем метод контроллера для перехода к сегменту
        if hasattr(self, '_timeline_controller') and marker_idx < len(self._timeline_controller.markers):
            marker = self._timeline_controller.markers[marker_idx]
            self._timeline_controller.seek_frame(marker.start_frame)

    def _on_shortcut_pressed(self, key: str):
        """Обработка нажатия горячей клавиши."""
        print(f"DEBUG: MainWindow._on_shortcut_pressed - key: {key}")
        
        if key == 'DELETE':
            self._delete_selected_segment()
        elif key == 'UNDO':
            self.undo_triggered.emit()
        elif key == 'REDO':
            self.redo_triggered.emit()
        elif key == 'PLAY_PAUSE':
            self.play_pause_triggered.emit()
        elif key == 'SKIP_LEFT':
            self.skip_seconds_triggered.emit(-5)
        elif key == 'SKIP_RIGHT':
            self.skip_seconds_triggered.emit(5)
        else:
            # Обработка остальных клавиш как событий
            self.key_pressed.emit(key)

    def _delete_selected_segment(self):
        """Удалить выделенный сегмент."""
        print("DEBUG: _delete_selected_segment called")
        
        # Сначала проверяем выделение в таблице сегментов
        if self.segment_list_widget and hasattr(self.segment_list_widget, 'table'):
            selected_rows = self.segment_list_widget.table.selectionModel().selectedRows()
            if selected_rows:
                # Получаем индекс выделенного сегмента из таблицы
                row = selected_rows[0].row()
                # Получаем marker_idx из первого столбца
                item = self.segment_list_widget.table.item(row, 0)
                if item and item.data(Qt.ItemDataRole.UserRole) is not None:
                    marker_idx = item.data(Qt.ItemDataRole.UserRole)
                    print(f"DEBUG: Deleting segment from table selection - marker_idx: {marker_idx}")
                    self._delete_marker_by_index(marker_idx)
                    return
        
        # Если в таблице ничего не выделено, проверяем выделение на таймлайне
        if hasattr(self, '_timeline_controller') and self._timeline_controller:
            # Проверяем выделенные маркеры в контроллере
            selected_markers = self._timeline_controller.get_selected_markers()
            if selected_markers:
                # Удаляем первый выделенный маркер
                marker_idx = selected_markers[0]
                print(f"DEBUG: Deleting selected segment from timeline - marker_idx: {marker_idx}")
                self._delete_marker_by_index(marker_idx)
                return
            
            # Если нет выделенных маркеров, удаляем последний добавленный маркер как fallback
            markers = self._timeline_controller.markers
            if markers:
                marker_idx = len(markers) - 1
                print(f"DEBUG: Deleting last segment as fallback - marker_idx: {marker_idx}")
                self._delete_marker_by_index(marker_idx)
            else:
                print("DEBUG: No segments to delete")
                # Можно показать сообщение пользователю
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Удаление", "Нет выделенных сегментов для удаления.")
    
    def _delete_marker_by_index(self, marker_idx: int):
        """Удалить маркер по индексу."""
        if hasattr(self, '_timeline_controller') and self._timeline_controller:
            print(f"DEBUG: Calling timeline_controller.delete_marker({marker_idx})")
            self._timeline_controller.delete_marker(marker_idx)

    def _on_playback_time_changed(self, frame_idx: int):
        """Обновление при изменении времени воспроизведения."""
        # Adapted from old version
        pass  # Implementation needed

    def _on_markers_changed(self):
        """Обновление списка отрезков с применением фильтров."""
        # Adapted from old version
        pass  # Implementation needed

    def _on_recording_status_changed(self, event_type: str, status: str):
        """Изменение статуса записи."""
        # Adapted from old version
        if status == "Recording":
            self.status_label.setText(f"🔴 Recording: {event_type}")
            self.status_label.setStyleSheet("color: #ff0000;")
        elif status == "Complete":
            self.status_label.setText(f"✓ Complete: {event_type}")
            self.status_label.setStyleSheet("color: #00ff00;")
        else:
            self.status_label.setText("Ready")
            self.status_label.setStyleSheet("color: #ffcc00;")

    def _on_timeline_update(self):
        """Обновление таймлайна при изменении фрейма."""
        # Adapted
        pass  # Implementation needed

    def _on_events_changed(self):
        """Обработка изменения событий - обновить shortcuts и фильтры."""
        self._setup_event_shortcuts()
        self._update_event_filter()

    def _on_events_changed_timeline(self):
        """Обработка изменения событий для таймлайна."""
        # Adapted
        pass  # Implementation needed

    def _on_frame_ready(self, frame):
        """Обработка готового кадра из контроллера."""
        # Adapted from old version
        if frame is None:
            return

        # Передаем кадр напрямую в ScalableVideoLabel
        self.video_label.set_frame(frame)

    def _on_autosave_completed(self):
        """Обработка завершения автосохранения."""
        # Adapted
        pass  # Implementation needed

    # ===== Menu Handlers =====

    def _on_new_project(self):
        """Создать новый проект."""
        self.new_project_triggered.emit()

    def _on_open_video(self):
        """Открыть видео."""
        self.open_video_triggered.emit()

    def _on_open_project(self):
        """Открыть проект."""
        self.load_project_triggered.emit()

    def _on_save_project(self):
        """Сохранить проект."""
        self.save_project_triggered.emit()

    def _on_save_project_as(self):
        """Сохранить проект как."""
        self.save_project_triggered.emit()

    def _on_preview_clicked(self):
        """Открыть окно предпросмотра."""
        self.open_preview_triggered.emit()

    def _on_settings_clicked(self):
        """Открыть настройки."""
        self.open_settings_triggered.emit()

    def _on_export_clicked(self):
        """Экспортировать."""
        self.export_triggered.emit()

    def _on_about(self):
        """О программе."""
        QMessageBox.about(self, "О программе", "Hockey Editor Pro - инструмент анализа хоккейных матчей")

    # ===== Shortcuts Setup =====

    def _setup_shortcuts(self):
        """Инициализировать горячие клавиши (adapted from old version)."""
        # Shortcuts are now handled by ShortcutController
        pass

    def _setup_event_shortcuts(self):
        """Создаёт глобальные горячие клавиши для всех событий."""
        # Shortcuts are now handled by ShortcutController
        pass

    # ===== Drag & Drop =====

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop events."""
        urls = event.mimeData().urls()
        if urls:
            video_path = urls[0].toLocalFile()
            # Emit signal for video loading
            self.open_video_triggered.emit()  # Controller will handle the path

    # ===== Status Updates =====

    def _update_status_bar(self):
        """Update status bar with current info."""
        # Adapted from old version
        pass  # Implementation needed

    def get_timeline_widget(self) -> TimelineWidget:
        """Get the timeline widget."""
        return self.timeline_widget

    def get_shortcuts_widget(self) -> Optional[QWidget]:
        """Get the shortcuts widget."""
        return getattr(self, 'shortcuts_widget', None)

    def update_mode_indicator(self, recording_mode: str, fixed_duration: int, pre_roll: float, post_roll: float):
        """Обновить индикатор режима записи."""
        if recording_mode == "fixed_length":
            mode_text = "Режим: Фиксированная длина"
            params_text = f"Длительность: {fixed_duration}с | Pre-roll: {pre_roll}с | Post-roll: {post_roll}с"
        else:
            mode_text = "Режим: Динамический"
            params_text = f"Pre-roll: {pre_roll}с | Post-roll: {post_roll}с"
        
        self.mode_indicator.setText(f"{mode_text} | {params_text}")

    def set_timeline_controller(self, controller) -> None:
        """Set the timeline controller and create timeline widget.

        Args:
            controller: TimelineController instance
        """
        # Создать timeline widget
        self.timeline_widget = TimelineWidget(controller)

        # Сохранить ссылку на контроллер
        self._timeline_controller = controller

        # Установить ссылку на главное окно в контроллере для корректной работы сигналов
        controller.set_main_window(self)

        # Добавить timeline widget в splitter
        central_widget = self.centralWidget()
        main_layout = central_widget.layout()
        main_splitter = main_layout.itemAt(0).widget()  # QSplitter

        # Добавить timeline widget как второй элемент splitter
        main_splitter.addWidget(self.timeline_widget)

    def open_segment_editor(self, segment_idx: int) -> None:
        """Открыть редактор сегмента.

        Args:
            segment_idx: Индекс сегмента для редактирования
        """
        # Получить маркер по индексу
        if hasattr(self, '_timeline_controller') and segment_idx < len(self._timeline_controller.markers):
            marker = self._timeline_controller.markers[segment_idx]

            # Получить MainController через TimelineController
            # MainController сохраняет ссылку на себя в TimelineController
            main_controller = getattr(self._timeline_controller, '_main_controller', None)

            if main_controller:
                from src.views.windows.instance_edit import InstanceEditWindow
                dialog = InstanceEditWindow(marker, main_controller, parent=self)

                # Подключить сигналы для обновления таймлайна при изменении маркера
                dialog.marker_updated.connect(lambda: self._on_segment_updated(segment_idx))
                dialog.accepted.connect(lambda: self._on_segment_updated(segment_idx))

                dialog.exec()
            else:
                # Fallback: показать сообщение об ошибке
                QMessageBox.warning(self, "Error", "Cannot open segment editor: controller not available")

    def _on_segment_updated(self, segment_idx: int):
        """Обработка обновления сегмента после редактирования.

        Args:
            segment_idx: Индекс обновленного сегмента
        """
        # Обновить таймлайн и список сегментов
        if hasattr(self, '_timeline_controller'):
            self._timeline_controller.refresh_view()
            self._timeline_controller.markers_changed.emit()

    # Drag and drop support
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Обработка входа drag-drop."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        """Обработка drop видеофайла."""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
                # Emit signal for video loading
                self.open_video_triggered.emit()
                break

    # Extended status bar methods
    def update_extended_status_bar(self, fps: float, current_frame: int, total_frames: int, speed: float, segment_count: int) -> None:
        """Обновить расширенный статус-бар с подробной информацией."""
        if fps > 0 and total_frames > 0:
            current_time = self._format_time_single(current_frame / fps)
            total_time = self._format_time_single(total_frames / fps)

            status = f"{current_time}/{total_time} | {segment_count} отрезков | FPS: {fps:.2f} | Speed: {speed:.2f}x"

            # Если воспроизведение, добавить индикатор
            if hasattr(self, '_is_playing') and self._is_playing:
                status = "▶ " + status

            self.status_bar.showMessage(status)
        else:
            self.status_bar.showMessage("Готов")

    def _format_time_single(self, seconds: float) -> str:
        """Форматировать время MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"

    # Filter methods
    def setup_filters(self) -> None:
        """Настроить фильтры для сегментов."""
        # Этот метод будет вызываться из контроллера
        pass

    def update_event_filter(self) -> None:
        """Обновить список доступных типов событий в фильтре."""
        # Этот метод будет реализован в контроллере
        pass

    # Additional signals
    video_dropped = Signal(str)  # Signal emitted when video is dropped (file_path)