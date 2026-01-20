# Импорты для работы из корня проекта (main.py добавляет src в sys.path)
from models.domain.project import Project
from models.config.app_settings import AppSettings
from services.video_engine import VideoService
from services.history import HistoryManager
from services.serialization import ProjectIO
from views.windows.main_window import MainWindow
from views.windows.settings_dialog import SettingsDialog
from controllers.playback_controller import PlaybackController
from controllers.timeline_controller import TimelineController
from controllers.project_controller import ProjectController
from controllers.export import ExportController
from controllers.shortcut_controller import ShortcutController
from controllers.filter_controller import FilterController
from controllers.instance_edit_controller import InstanceEditController
from controllers.settings_controller import SettingsController
from controllers.custom_event_controller import CustomEventController
from hockey_editor.utils.autosave import AutosaveManager
from PySide6.QtCore import QObject
from PySide6.QtGui import QPixmap


class MainController(QObject):
    """Главный контроллер приложения."""

    def __init__(self):
        # Создать модели
        self.project = Project(name="Untitled")
        self.settings = AppSettings()

        # Создать сервисы
        self.video_service = VideoService()
        self.history_manager = HistoryManager()
        self.project_io = ProjectIO()

        # Создать Views
        self.main_window = MainWindow()
        # Подключить closeEvent к main_window
        self.main_window.closeEvent = self.closeEvent

        # Создать контроллеры
        self.playback_controller = PlaybackController(
            self.video_service,
            self.main_window.get_player_controls(),
            self.main_window
        )

        # Создать дополнительные контроллеры
        self.shortcut_controller = ShortcutController(self.main_window)
        self.filter_controller = FilterController()

        # Создать timeline_controller ПЕРЕД созданием timeline_widget
        self.timeline_controller = TimelineController(
            self.project,
            None,  # timeline_widget будет установлен позже
            self.main_window.get_segment_list_widget(),
            self.history_manager,
            self.settings
        )

        # Связать timeline_controller с playback_controller
        self.timeline_controller.set_playback_controller(self.playback_controller)

        # Подключить сигналы для синхронизации плейхеда
        self.playback_controller.frame_changed.connect(lambda f: self.timeline_controller.seek_frame(f, update_playback=False))

        # Теперь создать timeline_widget с controller
        self.main_window.set_timeline_controller(self.timeline_controller)

        # Установить timeline_widget в controller
        self.timeline_controller.set_timeline_widget(self.main_window.get_timeline_widget())

        # Сохранить ссылку на timeline_controller в main_window для доступа из open_segment_editor
        self.main_window._timeline_controller = self.timeline_controller

        # --- ДОБАВИТЬ ЭТУ СТРОКУ ---
        self.timeline_controller.set_main_window(self.main_window)
        # ---------------------------

        # Сохранить ссылку на main_controller в timeline_controller для InstanceEditWindow
        self.timeline_controller._main_controller = self

        self.project_controller = ProjectController(self.project_io)
        self.project_controller.current_project = self.project  # Установить текущий проект

        # Создать менеджер автосохранения
        self.autosave_manager = AutosaveManager(self)
        self.autosave_manager.autosave_completed.connect(self._on_autosave_completed)

        # Создать export controller (lazy initialization)
        self.export_controller = None

        # Создать контроллеры для окон (lazy initialization)
        self._instance_edit_controller = None
        self._settings_controller = None
        self._custom_event_controller = None

        # Свойства для доступа из views
        self.markers = self.project.markers
        self.processor = self.video_service

        # Сигналы для обновления views
        from PySide6.QtCore import Signal
        self.markers_changed = Signal()
        self.playback_time_changed = Signal(int)

        # Настроить связи
        self._setup_connections()

        # Запустить автосохранение
        self.autosave_manager.start()

    def _setup_connections(self):
        """Настроить связи между компонентами."""
        # Связать timeline с playback (позиция плейхеда)
        # Note: PlayerControls больше не имеет сигнала seek_frame
        # Timeline обновляется через другие механизмы

        # Подключить сигналы меню
        self.main_window.open_video_triggered.connect(self._on_open_video)
        self.main_window.save_project_triggered.connect(self._on_save_project)
        self.main_window.load_project_triggered.connect(self._on_load_project)
        self.main_window.new_project_triggered.connect(self._on_new_project)
        self.main_window.open_settings_triggered.connect(self._on_open_settings)
        self.main_window.export_triggered.connect(self._on_export)
        self.main_window.open_preview_triggered.connect(self._on_open_preview)

        # Подключить сигнал клавиш от main_window и shortcut_controller
        self.main_window.key_pressed.connect(self._on_key_pressed)
        self.shortcut_controller.shortcut_pressed.connect(self._on_shortcut_pressed)

        # Подключить фильтры
        self.filter_controller.filters_changed.connect(self._on_filters_changed)

        # Подключить drag-drop
        self.main_window.video_dropped.connect(self._on_video_dropped)

    def _on_shortcut_pressed(self, key: str):
        """Обработка нажатия горячей клавиши из shortcut controller."""
        # Обработка специальных клавиш
        if key == 'PLAY_PAUSE':
            self.playback_controller.toggle_play_pause()
        elif key == 'OPEN_VIDEO':
            self._on_open_video()
        elif key == 'CANCEL':
            self.playback_controller.cancel_recording()
        elif key == 'UNDO':
            self.timeline_controller.undo()
        elif key == 'REDO':
            self.timeline_controller.redo()
        elif key == 'SKIP_LEFT':
            self._on_skip_seconds(-5)
        elif key == 'SKIP_RIGHT':
            self._on_skip_seconds(5)
        else:
            # Обработка событий (A, D, S, etc.)
            current_frame = self.playback_controller.current_frame
            fps = self.video_service.get_fps() if self.video_service.cap else 30.0
            self.timeline_controller.handle_hotkey(key, current_frame, fps)

    def _on_filters_changed(self):
        """Обработка изменения фильтров."""
        # Обновить отображение сегментов
        self.timeline_controller.refresh_view()

    def _on_video_dropped(self, file_path: str):
        """Обработка сброса видео файла."""
        if file_path:
            self.load_video(file_path)

    def _on_skip_seconds(self, seconds: int):
        """Перемотка на секунды."""
        fps = self.video_service.get_fps() if self.video_service.cap else 30.0
        if fps <= 0:
            return

        frames_to_skip = int(seconds * fps)
        current_frame = self.playback_controller.current_frame
        new_frame = max(0, min(self.video_service.get_total_frames() - 1, current_frame + frames_to_skip))
        self.playback_controller.seek_to_frame(new_frame)

    def _on_autosave_completed(self, success: bool, message: str):
        """Обработка завершения автосохранения."""
        if success:
            self.main_window.update_status_bar(f"✓ {message}")
        else:
            print(f"Autosave error: {message}")

    def run(self):
        """Запустить приложение."""
        self.main_window.show()

    def load_video(self, path: str) -> bool:
        """Загрузить видео."""
        success = self.playback_controller.load_video(path)
        if success:
            # Сохранить путь к видео в проекте
            self.project.video_path = path

            # Настроить timeline
            total_frames = self.video_service.get_total_frames()
            fps = self.video_service.get_fps() if self.video_service.cap else 30.0

            self.main_window.get_timeline_widget().set_total_frames(total_frames)
            self.main_window.get_timeline_widget().set_fps(fps)

            # Инициализировать дорожки
            self.timeline_controller.init_tracks(total_frames)

            # Обновить заголовок
            self.main_window.set_window_title(path.split('/')[-1])

        return success

    def add_marker(self, start_frame: int, end_frame: int, event_name: str):
        """Добавить маркер."""
        self.timeline_controller.add_marker(start_frame, end_frame, event_name)

    def delete_marker(self, marker_idx: int):
        """Удалить маркер."""
        self.timeline_controller.delete_marker(marker_idx)

    def get_fps(self):
        """Получить FPS видео."""
        return self.video_service.get_fps() if self.video_service.cap else 30.0

    def get_total_frames(self):
        """Получить общее количество кадров."""
        return self.video_service.get_total_frames()

    def get_playback_speed(self):
        """Получить скорость воспроизведения."""
        return self.playback_controller.get_speed()

    def _on_key_pressed(self, key: str):
        """Обработка нажатия горячей клавиши."""
        # Получить текущий кадр из playback controller
        current_frame = self.playback_controller.current_frame

        # Получить FPS из video service
        fps = self.video_service.get_fps() if self.video_service.cap else 30.0

        # Передать в timeline controller
        self.timeline_controller.handle_hotkey(key, current_frame, fps)

    def _on_open_video(self):
        """Обработка открытия видео."""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Open Video File",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*)"
        )

        if file_path:
            self.load_video(file_path)

    def _on_save_project(self):
        """Обработка сохранения проекта."""
        from PySide6.QtWidgets import QFileDialog

        # Если проект уже имеет путь, сохраняем туда
        if hasattr(self.project, 'file_path') and self.project.file_path:
            self.project_controller.save_project(self.project.file_path)
            return

        # Иначе спрашиваем путь
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Save Project",
            "project.hep",
            "Project Files (*.hep);;All Files (*)"
        )

        if file_path:
            # Убедимся, что расширение .hep
            if not file_path.endswith('.hep'):
                file_path += '.hep'

            success = self.project_controller.save_project(file_path)
            if success:
                self.project.file_path = file_path  # Сохраняем путь для будущих сохранений

    def _on_load_project(self):
        """Обработка загрузки проекта."""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Open Project",
            "",
            "Project Files (*.hep);;All Files (*)"
        )

        if file_path:
            loaded_project = self.project_controller.load_project(file_path)
            if loaded_project:
                # Заменяем текущий проект
                self.project = loaded_project
                self.project.file_path = file_path

                # Обновляем project_controller с новым проектом
                self.project_controller.current_project = self.project

                # Обновляем timeline controller с новым проектом
                self.timeline_controller.project = self.project
                self.timeline_controller.refresh_view()

                # Если в проекте есть видео, загружаем его
                if hasattr(self.project, 'video_path') and self.project.video_path:
                    self.load_video(self.project.video_path)

                # Обновляем заголовок
                self.main_window.set_window_title(f"{self.project.name} - {file_path.split('/')[-1]}")

    def _on_new_project(self):
        """Обработка создания нового проекта."""
        # Создаем новый проект
        self.project = Project(name="Untitled")

        # Обновляем project_controller с новым проектом
        self.project_controller.current_project = self.project

        # Очищаем timeline controller
        self.timeline_controller.project = self.project
        self.timeline_controller.refresh_view()

        # Останавливаем видео и очищаем VideoService
        self.playback_controller.pause()
        self.video_service.cleanup()

        # Сбрасываем состояние playback controller
        self.playback_controller.current_frame = 0
        self.playback_controller.playing = False

        # Очищаем интерфейс
        self.main_window.set_video_image(QPixmap())  # Очищаем видео экран
        self.main_window.set_window_title("Untitled")

        # Очищаем историю
        self.history_manager.clear_history()

    def _on_open_settings(self):
        """Обработка открытия окна настроек."""
        dialog = SettingsDialog(self.settings, self.main_window)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()

    def _on_export(self):
        """Обработка экспорта."""
        # Создать export controller если еще не создан
        if self.export_controller is None:
            video_path = getattr(self.project, 'video_path', '')
            fps = self.video_service.get_fps() if self.video_service.cap else 30.0
            self.export_controller = ExportController(self.project, video_path, fps)

        # Показать диалог экспорта
        self.export_controller.show_dialog()

    def _on_open_preview(self):
        """Обработка открытия окна предпросмотра."""
        self.open_preview_window()

    def open_preview_window(self):
        """Открыть окно предпросмотра отрезков."""
        # Создать и показать preview window
        from views.windows.preview_window import PreviewWindow
        preview_window = PreviewWindow(self, self.main_window)
        preview_window.show()

    def _on_settings_saved(self, new_settings: AppSettings):
        """Обработка сохранения настроек."""
        # Обновить настройки
        self.settings = new_settings

        # Обновить timeline controller
        self.timeline_controller.settings = self.settings

        # Обновить отображение (цвета маркеров могут измениться)
        self.timeline_controller.refresh_view()

        print("Settings updated successfully")

    # Controller factory methods
    def get_instance_edit_controller(self) -> InstanceEditController:
        """Get or create instance edit controller."""
        if self._instance_edit_controller is None:
            self._instance_edit_controller = InstanceEditController(self)
        return self._instance_edit_controller

    def get_settings_controller(self) -> SettingsController:
        """Get or create settings controller."""
        if self._settings_controller is None:
            self._settings_controller = SettingsController()
            # Load settings on first access
            self._settings_controller.load_settings()
        return self._settings_controller

    def get_custom_event_controller(self) -> CustomEventController:
        """Get or create custom event controller."""
        if self._custom_event_controller is None:
            self._custom_event_controller = CustomEventController()
        return self._custom_event_controller

    def closeEvent(self, event):
        """Закрытие окна."""
        self.autosave_manager.stop()

        # Cleanup controllers
        if self._instance_edit_controller:
            self._instance_edit_controller.cleanup()
        if self._settings_controller:
            self._settings_controller.cleanup()
        if self._custom_event_controller:
            self._custom_event_controller.cleanup()

        # self.playback_controller.cleanup()  # Метод cleanup не существует
        event.accept()
