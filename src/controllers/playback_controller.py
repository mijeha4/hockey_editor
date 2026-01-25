from PySide6.QtCore import QObject, QTimer, Signal, Qt
from PySide6.QtGui import QPixmap, QImage
import cv2
import numpy as np
# Используем абсолютные импорты для совместимости с run_test.py
try:
    from services.video_engine import VideoService
    from views.widgets.player_controls import PlayerControls
    from views.windows.main_window import MainWindow
except ImportError:
    # Для случаев, когда запускаем из src/
    from services.video_engine import VideoService
    from views.widgets.player_controls import PlayerControls
    from views.windows.main_window import MainWindow


class PlaybackController(QObject):
    """Контроллер управления воспроизведением видео."""

    # Сигнал для синхронизации плейхеда с timeline
    frame_changed = Signal(int)

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
        self._speed = 1.0  # Скорость воспроизведения

        # Подключить сигналы от View
        self.player_controls.playClicked.connect(self._on_play_clicked)
        self.player_controls.speedChanged.connect(self._on_speed_changed)
        self.player_controls.speedStepChanged.connect(self._on_speed_step_changed)

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

        # Синхронизировать плейхед на таймлайне
        self.frame_changed.emit(self.current_frame)

    def toggle_play_pause(self):
        """Переключить воспроизведение/паузу."""
        if self.playing:
            self.pause()
        else:
            self.play()

    def get_speed(self) -> float:
        """Возвращает текущую скорость воспроизведения."""
        return self._speed

    def _on_play_clicked(self):
        """Handle play/pause click from player controls."""
        if self.playing:
            self.pause()
        else:
            self.play()

    def _on_speed_step_changed(self, step: int):
        """Handle speed step change from player controls."""
        # Get current speed and adjust it
        current_speed = self.player_controls.get_current_speed()
        speeds = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]

        try:
            current_index = speeds.index(current_speed)
            new_index = max(0, min(len(speeds) - 1, current_index + step))
            new_speed = speeds[new_index]
            self.player_controls.set_speed(new_speed)
        except ValueError:
            # If current speed not in list, set to 1.0x
            self.player_controls.set_speed(1.0)

    def _on_speed_changed(self, speed: float):
        """Handle speed change from player controls."""
        self._speed = speed
        # For now, just print the speed change
        # In a full implementation, this would adjust playback speed
        print(f"Playback speed changed to: {speed}x")

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

        # Синхронизировать плейхед на таймлайне
        self.frame_changed.emit(self.current_frame)

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
        pixmap = pixmap.scaledToWidth(800, Qt.TransformationMode.SmoothTransformation)

        return pixmap
