from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QImage, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QLabel, QListWidget, QListWidgetItem, QFileDialog, QComboBox, QSpinBox,
    QMessageBox, QSpinBox
)
import cv2
import numpy as np
from pathlib import Path
from .timeline_graphics import TimelineWidget
from .edit_segment_dialog import EditSegmentDialog
from .settings_dialog import SettingsDialog
from ..models.marker import EventType
from ..utils.settings_manager import get_settings_manager
from ..utils.custom_events import get_custom_event_manager
from ..utils.shortcut_manager import ShortcutManager



class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.settings_manager = get_settings_manager()
        self.event_manager = get_custom_event_manager()
        self.event_manager.setParent(self)  # Ensure proper Qt object ownership
        self.shortcut_manager = ShortcutManager(self)
        
        # Автосохранение
        from ..utils.autosave import AutosaveManager
        self.autosave_manager = AutosaveManager(controller)
        self.autosave_manager.autosave_completed.connect(self._on_autosave_completed)
        
        self.setWindowTitle("Hockey Editor Pro - Professional Video Analysis")
        self.setGeometry(0, 0, 1800, 1000)
        self.setStyleSheet(self._get_dark_stylesheet())
        
        # Поддержка drag-drop для видео
        self.setAcceptDrops(True)
        
        self.setup_ui()
        self.connect_signals()
        self._setup_shortcuts()
        self._create_menu()

    def _create_menu(self):
        """Создать меню приложения."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = file_menu.addAction("New Project")
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_project)
        
        open_action = file_menu.addAction("Open Project")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_project)
        
        save_action = file_menu.addAction("Save Project")
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save_project)
        
        save_as_action = file_menu.addAction("Save Project As...")
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._on_save_project_as)
        
        file_menu.addSeparator()
        
        # Recent projects
        self.recent_menu = file_menu.addMenu("Recent Projects")
        self._update_recent_menu()
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self._on_about)

    def setup_ui(self):
        """Создать UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # ===== ВЕРХНЯЯ ЧАСТЬ (видео + список справа) =====
        top_layout = QHBoxLayout()
        
        # Видео (70%)
        video_layout = QVBoxLayout()
        
        # Видео виджет
        self.video_label = QLabel()
        self.video_label.setMinimumSize(800, 450)
        self.video_label.setStyleSheet("background-color: black; border: 1px solid grey;")
        video_layout.addWidget(self.video_label)
        
        # Контролы видео
        controls_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setMaximumWidth(80)
        self.play_btn.setToolTip("Play/Pause video (Space)")
        self.play_btn.clicked.connect(self._on_play_pause_clicked)
        controls_layout.addWidget(self.play_btn)
        
        # Ползунок прогресса
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setToolTip("Seek to frame")
        self.progress_slider.sliderMoved.connect(self._on_progress_slider_moved)
        controls_layout.addWidget(self.progress_slider)
        
        # Время
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setMaximumWidth(100)
        self.time_label.setToolTip("Current time / Total duration")
        controls_layout.addWidget(self.time_label)
        
        # Скорость (всегда 1x)
        speed_label = QLabel("1.0x")
        speed_label.setMaximumWidth(40)
        controls_layout.addWidget(speed_label)
        
        # Открыть видео
        open_btn = QPushButton("📁 Open")
        open_btn.setMaximumWidth(70)
        open_btn.setToolTip("Open video file (Ctrl+O)")
        open_btn.clicked.connect(self._on_open_video)
        controls_layout.addWidget(open_btn)
        
        video_layout.addLayout(controls_layout)
        top_layout.addLayout(video_layout, 7)
        
        # Список отрезков (30%)
        list_layout = QVBoxLayout()
        list_layout.addWidget(QLabel("Segments:"))
        
        self.markers_list = QListWidget()
        self.markers_list.itemDoubleClicked.connect(self._on_marker_double_clicked)
        list_layout.addWidget(self.markers_list)
        
        # Кнопки управления списком
        marker_btn_layout = QHBoxLayout()
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(self._on_delete_marker)
        marker_btn_layout.addWidget(delete_btn)
        
        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.clicked.connect(self._on_clear_markers)
        marker_btn_layout.addWidget(clear_btn)
        
        list_layout.addLayout(marker_btn_layout)
        
        top_layout.addLayout(list_layout, 3)
        
        main_layout.addLayout(top_layout)
        
        # ===== ТАЙМЛАЙН =====
        main_layout.addWidget(QLabel("Timeline:"))
        
        # 1. Передаем контроллер СРАЗУ в скобках
        self.timeline_widget = TimelineWidget(self.controller)
        
        # 2. Настраиваем ссылку на главное окно (для двойного клика)
        # В новом коде мы обращаемся к scene внутри виджета
        self.timeline_widget.scene.main_window = self
        
        # 3. Добавляем виджет на форму
        main_layout.addWidget(self.timeline_widget)
        
        # ===== КНОПКИ СОБЫТИЙ (динамические) И НАСТРОЙКИ =====
        event_layout = QHBoxLayout()

        # Контейнер для динамических кнопок событий
        self.event_buttons_layout = QHBoxLayout()
        event_layout.addLayout(self.event_buttons_layout)

        # Обновить кнопки из event_manager
        self._update_event_buttons()

        event_layout.addStretch()
        
        # Кнопки undo/redo
        undo_btn = QPushButton("↶ Undo")
        undo_btn.setMaximumWidth(80)
        undo_btn.setToolTip("Undo last operation (Ctrl+Z)")
        undo_btn.clicked.connect(self._on_undo_clicked)
        event_layout.addWidget(undo_btn)
        
        redo_btn = QPushButton("↷ Redo")
        redo_btn.setMaximumWidth(80)
        redo_btn.setToolTip("Redo last operation (Ctrl+Shift+Z)")
        redo_btn.clicked.connect(self._on_redo_clicked)
        event_layout.addWidget(redo_btn)
        
        # Кнопка просмотра
        preview_btn = QPushButton("👁️ Preview")
        preview_btn.setToolTip("Preview and filter segments")
        preview_btn.clicked.connect(self._on_preview_clicked)
        event_layout.addWidget(preview_btn)
        
        # Кнопка настроек
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.setToolTip("Open settings dialog (Ctrl+,)")
        settings_btn.clicked.connect(self._on_settings_clicked)
        event_layout.addWidget(settings_btn)
        
        # Кнопка экспорта
        export_btn = QPushButton("💾 Export")
        export_btn.setToolTip("Export segments to video (Ctrl+E)")
        export_btn.clicked.connect(self._on_export_clicked)
        event_layout.addWidget(export_btn)
        
        event_layout.addStretch()
        
        # Расширенный статус-бар
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #ffcc00;")
        self.status_label.setMinimumWidth(400)
        event_layout.addWidget(self.status_label)
        
        main_layout.addLayout(event_layout)
        
        central.setLayout(main_layout)
        
        # Подключить сигнал frame_ready для обновления видео
        self.controller.frame_ready.connect(self._on_frame_ready)

    def _create_event_button(self, text: str, color: str) -> QPushButton:
        """Создать кнопку события."""
        btn = QPushButton(text)
        btn.setMinimumSize(120, 90)
        btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: 2px solid {color};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {self._lighten_color(color)};
            }}
            QPushButton:pressed {{
                border: 3px solid yellow;
                background-color: {self._lighten_color(color)};
            }}
        """)
        return btn

    def _lighten_color(self, color_hex: str) -> str:
        """Светлая версия цвета для hover."""
        # Простая реализация
        return color_hex.replace("00", "33").replace("8b", "bb")

    def connect_signals(self):
        """Подключить сигналы контроллера."""
        self.controller.playback_time_changed.connect(self._on_playback_time_changed)
        self.controller.markers_changed.connect(self._on_markers_changed)
        self.controller.recording_status_changed.connect(self._on_recording_status_changed)
        self.controller.timeline_update.connect(self._on_timeline_update)
        self.controller.frame_ready.connect(self._on_frame_ready)

        # Подключить сигнал изменения событий
        self.event_manager.events_changed.connect(self._on_events_changed)
        self.event_manager.events_changed.connect(self._on_events_changed_timeline)

        # Запустить автосохранение
        self.autosave_manager.start()

    def _on_play_pause_clicked(self):
        """Кнопка Play/Pause - переключение."""
        self.controller.toggle_play_pause()
        self._update_play_btn_text()

    def _update_play_btn_text(self):
        """Обновить текст кнопки Play/Pause."""
        if self.controller.playing:
            self.play_btn.setText("⏸ Pause")
        else:
            self.play_btn.setText("▶ Play")

    def _on_progress_slider_moved(self):
        """Движение ползунка прогресса."""
        frame_idx = self.progress_slider.value()
        self.controller.seek_frame(frame_idx)

    def _on_open_video(self):
        """Открыть видео."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Video", "", "Videos (*.mp4 *.avi *.mov *.mkv);;All (*.*)"
        )
        if path:
            if self.controller.load_video(path):
                self.status_label.setText(f"✓ Loaded: {path.split('/')[-1]}")
                self._update_play_btn_text()
                self.progress_slider.setMaximum(self.controller.get_total_frames())
            else:
                QMessageBox.critical(self, "Error", "Failed to load video")

    def _on_event_btn_clicked(self, event_name: str):
        """Нажатие кнопки события."""
        self.controller.on_hotkey_pressed(event_name.upper())  # Контроллер ожидает key (строка)

    def _on_undo_clicked(self):
        """Отменить операцию."""
        self.controller.undo()
        self._on_markers_changed()
    
    def _on_redo_clicked(self):
        """Повторить операцию."""
        self.controller.redo()
        self._on_markers_changed()

    def _on_preview_clicked(self):
        """Открыть окно предпросмотра отрезков."""
        if not self.controller.markers:
            QMessageBox.warning(self, "Warning", "No segments to preview")
            return
        
        from .preview_window import PreviewWindow
        self.preview_window = PreviewWindow(self.controller, self)
        self.preview_window.show()

    def _on_settings_clicked(self):
        """Открыть настройки."""
        dialog = SettingsDialog(self.controller, self)
        if dialog.exec():
            # Переподключить горячие клавиши, если они изменились
            self._rebind_hotkeys()

    def _on_export_clicked(self):
        """Экспортировать видео."""
        if not self.controller.markers:
            QMessageBox.warning(self, "Warning", "No segments to export")
            return
        
        from .export_dialog import ExportDialog
        dialog = ExportDialog(self.controller, self)
        dialog.exec()

    def _on_marker_double_clicked(self, item: QListWidgetItem):
        """Двойной клик на отрезок = редактирование."""
        marker_idx = item.data(Qt.ItemDataRole.UserRole)
        marker = self.controller.markers[marker_idx]
        dialog = EditSegmentDialog(marker, self.controller.get_fps(), self)
        if dialog.exec():
            new_marker = dialog.get_marker()
            self.controller.markers[marker_idx] = new_marker
            self.controller.markers_changed.emit()
            self.controller.timeline_update.emit()

    def _on_delete_marker(self):
        """Удалить выбранный отрезок."""
        current_idx = self.markers_list.currentRow()
        if current_idx >= 0:
            marker_idx = self.markers_list.item(current_idx).data(Qt.ItemDataRole.UserRole)
            self.controller.delete_marker(marker_idx)

    def _on_clear_markers(self):
        """Удалить все отрезки."""
        reply = QMessageBox.question(self, "Confirm", "Delete all segments?")
        if reply == QMessageBox.StandardButton.Yes:
            self.controller.clear_markers()

    def _on_playback_time_changed(self, frame_idx: int):
        """Обновление при изменении времени воспроизведения."""
        fps = self.controller.get_fps()
        total_frames = self.controller.get_total_frames()
        
        self.progress_slider.blockSignals(True)
        self.progress_slider.setValue(frame_idx)
        self.progress_slider.blockSignals(False)
        
        # Обновить время
        if fps > 0:
            current_sec = frame_idx / fps
            total_sec = total_frames / fps
            self.time_label.setText(self._format_time(current_sec, total_sec))
        
        # Обновить расширенный статус-бар
        self._update_status_bar()

    def _on_markers_changed(self):
        """Обновление списка отрезков."""
        self.markers_list.clear()
        fps = self.controller.get_fps()

        for idx, marker in enumerate(self.controller.markers):
            start_time = self._format_time_single(marker.start_frame / fps if fps > 0 else 0)
            end_time = self._format_time_single(marker.end_frame / fps if fps > 0 else 0)
            text = f"{idx+1}. {marker.event_name} ({start_time}–{end_time})"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, idx)  # Сохранить оригинальный индекс маркера
            self.markers_list.addItem(item)

        # Обновить расширенный статус-бар
        self._update_status_bar()

    def _on_recording_status_changed(self, event_type: str, status: str):
        """Изменение статуса записи."""
        if status == "Recording":
            self.status_label.setText(f"🔴 Recording: {event_type}")
            self.status_label.setStyleSheet("color: #ff0000;")
        elif status == "Complete":
            self.status_label.setText(f"✓ Complete: {event_type}")
            self.status_label.setStyleSheet("color: #00ff00;")
        elif status == "Fixed":
            self.status_label.setText(f"✓ Fixed: {event_type}")
            self.status_label.setStyleSheet("color: #00ff00;")
        elif status == "Cancelled":
            self.status_label.setText("⏹️ Cancelled")
            self.status_label.setStyleSheet("color: #ffcc00;")
        else:
            self.status_label.setText("Ready")
            self.status_label.setStyleSheet("color: #ffcc00;")

    def _on_timeline_update(self):
        """Обновление таймлайна при изменении фрейма."""
        if hasattr(self.timeline_widget, 'scene_obj'):
            current_frame = self.controller.get_current_frame_idx()
            self.timeline_widget.scene_obj.update_playhead(current_frame)

    # ИСПРАВЛЕНО: удален дублированный метод _setup_shortcuts с EventType

    def _on_events_changed(self):
        """Обработка изменения событий - обновить кнопки и shortcuts."""
        self._update_event_buttons()
        self._setup_event_shortcuts()

    def _on_events_changed_timeline(self):
        """Обработка изменения событий для таймлайна."""
        if hasattr(self.timeline_widget, 'scene_obj'):
            self.timeline_widget.scene_obj.update_scene()

    def _update_event_buttons(self):
        """Обновить кнопки событий на основе CustomEventManager."""
        # Очистить существующие кнопки
        for i in reversed(range(self.event_buttons_layout.count())):
            widget = self.event_buttons_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # Создать новые кнопки для каждого события
        events = self.event_manager.get_all_events()
        for event in events:
            text = f"{event.shortcut.upper()}\n{event.name}"
            btn = self._create_event_button(text, event.color)
            btn.clicked.connect(lambda checked, e=event.name: self._on_event_btn_clicked(e))
            btn.setToolTip(f"Add {event.name} event ({event.shortcut.upper()})")
            self.event_buttons_layout.addWidget(btn)

    def _setup_shortcuts(self):
        """Инициализировать горячие клавиши через ShortcutManager."""
        # Очистить старые shortcuts для событий (если есть)
        for event in self.event_manager.get_all_events():
            self.shortcut_manager.unregister_shortcut(event.name.upper())

        # Зарегистрировать shortcuts для всех событий
        self._setup_event_shortcuts()

        # Регистрировать shortcuts для основных функций
        self.shortcut_manager.register_shortcut('PLAY_PAUSE', 'Space', self._on_play_pause_clicked)
        self.shortcut_manager.register_shortcut('OPEN_VIDEO', 'Ctrl+O', self._on_open_video)
        self.shortcut_manager.register_shortcut('CANCEL', 'Escape', self._on_cancel_recording)
        self.shortcut_manager.register_shortcut('SETTINGS', 'Ctrl+Comma', self._on_settings_clicked)
        self.shortcut_manager.register_shortcut('EXPORT', 'Ctrl+E', self._on_export_clicked)
        self.shortcut_manager.register_shortcut('UNDO', 'Ctrl+Z', self._on_undo_clicked)
        self.shortcut_manager.register_shortcut('REDO', 'Ctrl+Shift+Z', self._on_redo_clicked)

    def _setup_event_shortcuts(self):
        """Создаёт глобальные горячие клавиши для всех событий (A, D, S и кастомные)."""
        if hasattr(self, '_event_shortcuts'):
            for s in self._event_shortcuts:
                s.activated.disconnect()
                s.setParent(None)
            self._event_shortcuts.clear()
        else:
            self._event_shortcuts = []

        for event in self.event_manager.get_all_events():
            if not event.shortcut:
                continue

            shortcut = QShortcut(QKeySequence(event.shortcut.upper()), self)
            # ПРАВИЛЬНЫЙ вызов — передаём только строку с клавишей
            shortcut.activated.connect(
                lambda checked=False, key=event.shortcut.upper(): self.controller.on_hotkey_pressed(key)
            )
            self._event_shortcuts.append(shortcut)

    def _rebind_hotkeys(self):
        """Переподключить горячие клавиши после изменений в настройках."""
        # Перерегистрировать все shortcuts
        self._setup_shortcuts()

    def _on_cancel_recording(self):
        """Отмена записи (Escape)."""
        self.controller.cancel_recording()
        self._update_play_btn_text()

    def _on_selection_changed(self) -> None:
        """Handle event selection change."""
        selected = self.event_list.selectedItems()
        has_selection = len(selected) > 0
        
        self.edit_btn.setEnabled(has_selection)
        
        # Can only delete non-default events
        if has_selection:
            event_name = selected[0].data(Qt.UserRole) 
            event = self.manager.get_event(event_name)
            
            # Проверка на None
            if event is None:
                self.delete_btn.setEnabled(False)
                return
            
            is_default = event.name in {e.name for e in self.manager.DEFAULT_EVENTS}
            self.delete_btn.setEnabled(has_selection and not is_default)
        else:
            self.delete_btn.setEnabled(False)

    def _update_video_frame(self):
        """Обновить видео кадр на экране (через сигнал frame_ready)."""
        pass  # Видео обновляется через frame_ready сигнал

    def _on_frame_ready(self, frame):
        """Обработка готового кадра из контроллера."""
        if frame is None:
            return
        
        # Конвертировать BGR в RGB
        import cv2
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Масштабировать под размер label
        pixmap = QPixmap.fromImage(qt_image)
        pixmap = pixmap.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)
        self.video_label.setPixmap(pixmap)

    def _format_time(self, current_sec: float, total_sec: float) -> str:
        """Форматировать время MM:SS / MM:SS."""
        def fmt(s):
            m = int(s) // 60
            s = int(s) % 60
            return f"{m:02d}:{s:02d}"
        return f"{fmt(current_sec)} / {fmt(total_sec)}"

    def _format_time_single(self, seconds: float) -> str:
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
        QLabel {
            color: #ffffff;
        }
        QComboBox {
            background-color: #333333;
            color: #ffffff;
            border: 1px solid #555555;
        }
        """

    # ===== MENU HANDLERS =====
    
    def _on_new_project(self):
        """Создать новый проект."""
        self.controller.markers.clear()
        self.controller.markers_changed.emit()
        QMessageBox.information(self, "New Project", "Project cleared")
    
    def _on_open_project(self):
        """Открыть сохраненный проект."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "Hockey Editor Projects (*.hep);;All Files (*)"
        )
        
        if path:
            if self.controller.load_project(path):
                QMessageBox.information(self, "Success", f"Project loaded: {path}")
            else:
                QMessageBox.critical(self, "Error", f"Failed to load project: {path}")
    
    def _on_save_project(self):
        """Сохранить проект."""
        if not hasattr(self, 'current_project_path') or not self.current_project_path:
            self._on_save_project_as()
        else:
            if self.controller.save_project(self.current_project_path):
                QMessageBox.information(self, "Success", "Project saved")
            else:
                QMessageBox.critical(self, "Error", "Failed to save project")
    
    def _on_save_project_as(self):
        """Сохранить проект как новый файл."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project As", "", "Hockey Editor Projects (*.hep);;All Files (*)"
        )
        
        if path:
            if self.controller.save_project(path):
                self.current_project_path = path
                self.setWindowTitle(f"Hockey Editor Pro - {Path(path).name}")
                QMessageBox.information(self, "Success", "Project saved")
            else:
                QMessageBox.critical(self, "Error", "Failed to save project")
    
    def _update_recent_menu(self):
        """Обновить меню недавних проектов."""
        self.recent_menu.clear()
        
        recent_projects = self.controller.get_recent_projects()
        if not recent_projects:
            self.recent_menu.addAction("(No recent projects)")
            return
        
        for path in recent_projects:
            action = self.recent_menu.addAction(Path(path).name)
            action.triggered.connect(lambda checked, p=path: self._on_recent_project(p))
    
    def _on_recent_project(self, path: str):
        """Открыть недавний проект."""
        if self.controller.load_project(path):
            QMessageBox.information(self, "Success", f"Project loaded: {path}")
            self._update_recent_menu()
        else:
            QMessageBox.critical(self, "Error", f"Failed to load project: {path}")
    
    def _on_about(self):
        """О приложении."""
        QMessageBox.information(
            self, "About Hockey Editor Pro",
            "Hockey Editor Pro v1.0\n"
            "Professional Video Analysis Tool\n\n"
            "Hotkeys:\n"
            "A - Attack\n"
            "D - Defense\n"
            "S - Shift\n"
            "Space - Play/Pause\n"
            "Ctrl+O - Open Video\n"
            "Ctrl+E - Export\n"
            "Ctrl+, - Settings"
        )

    def _on_autosave_completed(self, success: bool, message: str):
        """Обработка завершения автосохранения."""
        if success:
            self.status_label.setText(f"✓ {message}")
        else:
            print(f"Autosave error: {message}")

    def dragEnterEvent(self, event):
        """Обработка входа drag-drop."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Обработка drop видеофайла."""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')):
                self.controller.load_video(file_path)
                break

    def open_segment_editor(self, marker_idx: int):
        """Открыть редактор сегмента (вызывается из timeline при double-click)."""
        if 0 <= marker_idx < len(self.controller.markers):
            marker = self.controller.markers[marker_idx]
            dialog = EditSegmentDialog(marker, self.controller.get_fps(), self)
            if dialog.exec():
                new_marker = dialog.get_marker()
                self.controller.markers[marker_idx] = new_marker
                self.controller.markers_changed.emit()
                self.controller.timeline_update.emit()
    
    def _update_status_bar(self):
        """Обновить расширенный статус-бар с подробной информацией."""
        fps = self.controller.get_fps()
        current_frame = self.controller.get_current_frame_idx()
        total_frames = self.controller.get_total_frames()
        
        if fps > 0 and total_frames > 0:
            current_time = self._format_time_single(current_frame / fps)
            total_time = self._format_time_single(total_frames / fps)
            segment_count = len(self.controller.markers)
            
            status = f"{current_time}/{total_time} | {segment_count} segments | FPS: {fps:.2f}"
            
            # Если воспроизведение, добавить индикатор
            if self.controller.playing:
                status = "▶ " + status
            
            self.status_label.setText(status)
        else:
            self.status_label.setText("Ready")

    def closeEvent(self, event):
        """Закрытие окна."""
        self.autosave_manager.stop()
        self.controller.cleanup()
        event.accept()
