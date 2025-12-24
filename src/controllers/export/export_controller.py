from PySide6.QtCore import QThread, Signal, QObject
from typing import List, Dict

# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.marker import Marker
    from models.domain.project import Project
    from services.export import VideoExporter
    from views.windows.export_dialog import ExportDialog
except ImportError:
    # Для случаев, когда запускаем из src/
    from ...models.domain.marker import Marker
    from ...models.domain.project import Project
    from ...services.export import VideoExporter
    from ...views.windows.export_dialog import ExportDialog


class ExportWorker(QThread):
    """Worker thread для экспорта видео без блокировки UI."""

    progress = Signal(int)  # 0-100
    finished = Signal(bool, str)  # (success, message)

    def __init__(self, video_path: str, markers: List[Marker], fps: float, params: Dict):
        super().__init__()
        self.video_path = video_path
        self.markers = markers
        self.fps = fps
        self.params = params
        self.is_cancelled = False

    def run(self):
        """Запустить экспорт в отдельном потоке."""
        try:
            self.progress.emit(0)

            # Создать экспортер
            exporter = VideoExporter()

            # Запустить экспорт
            success = exporter.export_segments(
                video_path=self.video_path,
                markers=self.markers,
                fps=self.fps,
                output_path=self.params['output_path'],
                codec=self.params['codec'],
                quality=self.params['quality'],
                resolution=self.params['resolution'],
                include_audio=self.params['include_audio'],
                merge_segments=self.params['merge_segments']
            )

            self.progress.emit(100)

            if success:
                if self.params['merge_segments']:
                    message = f"Export completed: {self.params['output_path']}"
                else:
                    message = f"Export completed: {len(self.markers)} separate files in {self.params['output_path']}"
            else:
                message = "Export failed"

            self.finished.emit(success, message)

        except Exception as e:
            self.finished.emit(False, f"Export failed: {str(e)}")

    def cancel(self):
        """Отменить экспорт."""
        self.is_cancelled = True


class ExportController(QObject):
    """Контроллер управления экспортом видео."""

    def __init__(self, project: Project, video_path: str, fps: float):
        super().__init__()
        self.project = project
        self.video_path = video_path
        self.fps = fps

        # Создать View
        self.view = ExportDialog()

        # Создать worker для экспорта
        self.export_worker = None

        # Подключить сигналы
        self._connect_signals()

    def _connect_signals(self):
        """Подключить сигналы View к методам Controller."""
        self.view.export_requested.connect(self._on_export_requested)

    def show_dialog(self):
        """Показать диалог экспорта."""
        # Подготовить данные сегментов для View
        segments_data = self._prepare_segments_data()
        self.view.set_segments(segments_data)

        # Показать диалог
        self.view.exec()

    def _prepare_segments_data(self) -> List[Dict]:
        """Подготовить данные сегментов для View."""
        segments_data = []

        for i, marker in enumerate(self.project.markers):
            duration_sec = (marker.end_frame - marker.start_frame) / self.fps if self.fps > 0 else 0

            segments_data.append({
                'id': i,
                'event_name': marker.event_name,
                'start_frame': marker.start_frame,
                'end_frame': marker.end_frame,
                'duration_sec': duration_sec
            })

        return segments_data

    def _on_export_requested(self, params: Dict):
        """Обработка запроса на экспорт."""
        # Получить выбранные маркеры
        selected_segment_ids = params['selected_segment_ids']
        selected_markers = [self.project.markers[i] for i in selected_segment_ids]

        if not selected_markers:
            return

        # Отключить элементы управления
        self.view.set_controls_enabled(False)

        # Создать worker для экспорта
        self.export_worker = ExportWorker(
            video_path=self.video_path,
            markers=selected_markers,
            fps=self.fps,
            params=params
        )

        # Подключить сигналы worker
        self.export_worker.progress.connect(self._on_progress_update)
        self.export_worker.finished.connect(self._on_export_finished)

        # Запустить экспорт
        self.view.set_progress(0, "Exporting...")
        self.export_worker.start()

    def _on_progress_update(self, value: int):
        """Обновить прогресс."""
        self.view.set_progress(value, f"Exporting... {value}%")

    def _on_export_finished(self, success: bool, message: str):
        """Экспорт завершен."""
        # Включить элементы управления
        self.view.set_controls_enabled(True)

        # Показать результат
        self.view.show_export_result(success, message)

        # Очистить worker
        self.export_worker = None
