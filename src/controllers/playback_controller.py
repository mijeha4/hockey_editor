from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QPixmap, QImage
import cv2
import numpy as np
# Используем абсолютные импорты для совместимости с run_test.py
try:
    from services.video_engine import VideoService
    from views.components.player_controls import PlayerControls
    from views.windows.main_window import MainWindow
except ImportError:
    # Для случаев, когда запускаем из src/
    from ..services.video_engine import VideoService
    from ..views.components.player_controls import PlayerControls
    from ..views.windows.main_window import MainWindow


class PlaybackController(QObject):
    """Контроллер управления воспроизведением видео."""

    def __init__(self, video_service: VideoService,
                 player_controls: PlayerControls,
                 main_window: MainWindow):
        super().__init__()

        self.video_service = video_service
        self.player_controls = player_controls
        self.main_window = main_window

        # Таймер воспроизведения
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)

        self.playing = False
        self.current_frame = 0

        # Подключить сигналы от View
        self.player_controls.play_clicked.connect(self.play)
        self.player_controls.pause_clicked.connect(self.pause)
        self.player_controls.seek_requested.connect(self.seek_to_frame)

    def load_video(self, video_path: str) -> bool:
        """Загрузить видео."""
        try:
            success = self.video_service.load_video(video_path)
            if success:
                # Настроить UI
                total_frames = self.video_service.get_total_frames()
                self.player_controls.set_duration(total_frames)
                self.player_controls.set_current_frame(0)

                # Показать первый кадр
                self.current_frame = 0
                self._display_current_frame()

                # Остановить воспроизведение
                self.pause()

            return success
        except Exception as e:
            print(f"Error loading video: {e}")
            return False

    def play(self):
        """Начать воспроизведение."""
        if not self.video_service.cap or self.playing:
            return

        self.playing = True
        # Рассчитать интервал на основе FPS
        fps = self.video_service.get_fps()
        interval_ms = int(1000 / fps) if fps > 0 else 33
        self.playback_timer.start(interval_ms)

    def pause(self):
        """Пауза."""
        self.playing = False
        self.playback_timer.stop()

    def seek_to_frame(self, frame_idx: int):
        """Перемотать на кадр."""
        self.current_frame = frame_idx
        self._display_current_frame()

    def _on_playback_tick(self):
        """Таймер воспроизведения."""
        if not self.playing:
            return

        # Перейти к следующему кадру
        self.current_frame += 1

        # Проверить границы
        total_frames = self.video_service.get_total_frames()
        if self.current_frame >= total_frames:
            self.current_frame = total_frames - 1
            self.pause()
            return

        # Обновить UI
        self.player_controls.set_current_frame(self.current_frame)
        self._display_current_frame()

    def _display_current_frame(self):
        """Показать текущий кадр."""
        try:
            # Получить кадр из сервиса
            frame = self.video_service.get_frame(self.current_frame)

            # Конвертировать numpy array в QPixmap
            pixmap = self._numpy_to_pixmap(frame)

            # Показать в MainWindow
            self.main_window.set_video_image(pixmap)

        except Exception as e:
            print(f"Error displaying frame: {e}")

    def _numpy_to_pixmap(self, frame: np.ndarray) -> QPixmap:
        """Конвертировать numpy array (BGR) в QPixmap."""
        # Конвертировать BGR в RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w

        # Создать QImage
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # Конвертировать в QPixmap
        pixmap = QPixmap.fromImage(qt_image)

        # Масштабировать для отображения
        pixmap = pixmap.scaledToWidth(800, QPixmap.TransformationMode.SmoothTransformation)

        return pixmap
