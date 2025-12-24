# Используем абсолютные импорты для совместимости с run_test.py
try:
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
except ImportError:
    # Для случаев, когда запускаем из src/
    from ..models.domain.project import Project
    from ..models.config.app_settings import AppSettings
    from ..services.video_engine import VideoService
    from ..services.history import HistoryManager
    from ..services.serialization import ProjectIO
    from ..views.windows.main_window import MainWindow
    from ..views.windows.settings_dialog import SettingsDialog
    from .playback_controller import PlaybackController
    from .timeline_controller import TimelineController
    from .project_controller import ProjectController
    from .export import ExportController


class MainController:
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

        # Создать контроллеры
        self.playback_controller = PlaybackController(
            self.video_service,
            self.main_window.get_player_controls(),
            self.main_window
        )

        self.timeline_controller = TimelineController(
            self.project,
            self.main_window.get_timeline_view().scene,
            self.main_window.get_segment_list(),  # Добавить ссылку на SegmentList
            self.history_manager,
            self.settings  # Добавить настройки
        )

        self.project_controller = ProjectController(self.project_io)

        # Создать export controller (lazy initialization)
        self.export_controller = None

        # Настроить связи
        self._setup_connections()

    def _setup_connections(self):
        """Настроить связи между компонентами."""
        # Связать timeline с playback (позиция плейхеда)
        self.playback_controller.player_controls.seek_requested.connect(
            lambda frame: self.main_window.get_timeline_view().set_playhead_position(frame)
        )

        # Подключить сигналы меню
        self.main_window.open_video_triggered.connect(self._on_open_video)
        self.main_window.save_project_triggered.connect(self._on_save_project)
        self.main_window.load_project_triggered.connect(self._on_load_project)
        self.main_window.new_project_triggered.connect(self._on_new_project)
        self.main_window.open_settings_triggered.connect(self._on_open_settings)
        self.main_window.export_triggered.connect(self._on_export)

        # Подключить сигнал клавиш
        self.main_window.key_pressed.connect(self._on_key_pressed)

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
            self.main_window.get_timeline_view().set_duration(total_frames)

            # Инициализировать дорожки
            self.timeline_controller.init_tracks(total_frames)

            # Обновить заголовок
            self.main_window.set_window_title(path.split('/')[-1])

        return success

    def add_marker(self, start_frame: int, end_frame: int, event_name: str):
        """Добавить маркер."""
        self.timeline_controller.add_marker(start_frame, end_frame, event_name)

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
            "project.json",
            "Project Files (*.json);;All Files (*)"
        )

        if file_path:
            # Убедимся, что расширение .json
            if not file_path.endswith('.json'):
                file_path += '.json'

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
            "Project Files (*.json);;All Files (*)"
        )

        if file_path:
            loaded_project = self.project_controller.load_project(file_path)
            if loaded_project:
                # Заменяем текущий проект
                self.project = loaded_project
                self.project.file_path = file_path

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

        # Очищаем timeline controller
        self.timeline_controller.project = self.project
        self.timeline_controller.refresh_view()

        # Останавливаем видео
        self.playback_controller.pause()

        # Очищаем интерфейс
        self.main_window.set_video_image(QPixmap())  # Очищаем видео экран
        self.main_window.set_window_title("Untitled")

        # Очищаем историю
        self.history_manager.clear()

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

    def _on_settings_saved(self, new_settings: AppSettings):
        """Обработка сохранения настроек."""
        # Обновить настройки
        self.settings = new_settings

        # Обновить timeline controller
        self.timeline_controller.settings = self.settings

        # Обновить отображение (цвета маркеров могут измениться)
        self.timeline_controller.refresh_view()

        print("Settings updated successfully")
