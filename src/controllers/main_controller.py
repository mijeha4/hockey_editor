# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.project import Project
    from models.config.app_settings import AppSettings
    from services.video_engine import VideoService
    from services.history import HistoryManager
    from services.serialization import ProjectIO
    from views.windows.main_window import MainWindow
    from controllers.playback_controller import PlaybackController
    from controllers.timeline_controller import TimelineController
    from controllers.project_controller import ProjectController
except ImportError:
    # Для случаев, когда запускаем из src/
    from ..models.domain.project import Project
    from ..models.config.app_settings import AppSettings
    from ..services.video_engine import VideoService
    from ..services.history import HistoryManager
    from ..services.serialization import ProjectIO
    from ..views.windows.main_window import MainWindow
    from .playback_controller import PlaybackController
    from .timeline_controller import TimelineController
    from .project_controller import ProjectController


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
            self.history_manager
        )

        self.project_controller = ProjectController(self.project_io)

        # Настроить связи
        self._setup_connections()

    def _setup_connections(self):
        """Настроить связи между компонентами."""
        # Связать timeline с playback (позиция плейхеда)
        self.playback_controller.player_controls.seek_requested.connect(
            lambda frame: self.main_window.get_timeline_view().set_playhead_position(frame)
        )

    def run(self):
        """Запустить приложение."""
        self.main_window.show()

    def load_video(self, path: str) -> bool:
        """Загрузить видео."""
        success = self.playback_controller.load_video(path)
        if success:
            # Настроить timeline
            total_frames = self.video_service.get_total_frames()
            self.main_window.get_timeline_view().set_duration(total_frames)

            # Обновить заголовок
            self.main_window.set_window_title(path.split('/')[-1])

        return success

    def add_marker(self, start_frame: int, end_frame: int, event_name: str):
        """Добавить маркер."""
        self.timeline_controller.add_marker(start_frame, end_frame, event_name)
