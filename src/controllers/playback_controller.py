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
    # Сигнал с уже подготовленным изображением кадра (для Preview/InstanceEdit),
    # чтобы не декодировать/конвертировать один и тот же кадр в нескольких окнах.
    pixmap_changed = Signal(QPixmap, int)  # pixmap, frame_idx

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

        # Последний отрисованный кадр (как QPixmap) для переиспользования другими окнами
        self._last_pixmap: QPixmap | None = None
        self._last_pixmap_frame: int | None = None

        # Таймер для "отложенного" обновления кадра при частых перемотках/кликах.
        # Идея: если пользователь быстро кликает по таймлайну или жмёт +-5 сек,
        # мы не будем каждый раз декодировать и показывать кадр, а подождём
        # небольшой интервал и покажем только последний выбранный кадр.
        self.seek_update_timer = QTimer()
        self.seek_update_timer.setSingleShot(True)
        self.seek_update_timer.timeout.connect(self._display_current_frame)

        # Кэш для масштабированных кадров.
        # ВАЖНО: ключом используем (frame_index, width, height), а НЕ содержимое кадра,
        # чтобы избежать дорогостоящего hash(frame.tobytes()), которое сильно тормозит
        # воспроизведение и перемотку на больших видео.
        self.frame_cache = {}
        self.cache_size = 100  # Максимальное количество кэшируемых кадров
        self.target_width = 800  # Целевая ширина для масштабирования
        self.use_high_quality_scaling = False  # Флаг для высококачественного масштабирования

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
        # Рассчитать интервал на основе FPS и скорости воспроизведения
        fps = self.video_service.get_fps()
        interval_ms = int(1000 / (fps * self._speed)) if fps > 0 else 33
        self.playback_timer.start(interval_ms)

    def pause(self):
        """Пауза."""
        self.playing = False
        self.playback_timer.stop()

    def seek_to_frame(self, frame_idx: int):
        """Перемотать на кадр."""
        self.current_frame = frame_idx

        # Отложенное обновление кадра для снижения нагрузки при частых перемотках.
        # Если пользователь быстро меняет позицию, предыдущий запрос на отрисовку
        # отменяется, и в итоге отрисуется только последнее положение.
        if self.seek_update_timer.isActive():
            self.seek_update_timer.stop()
        # Небольшая задержка (в мс); можно варьировать от 20 до 50.
        self.seek_update_timer.start(30)

        # Синхронизировать плейхед на таймлайне
        self.frame_changed.emit(self.current_frame)

    def seek_to_frame_immediate(self, frame_idx: int):
        """Перемотать на кадр и отрисовать сразу (без debounce).

        Используется для покадрового воспроизведения в предпросмотре/редакторе отрезков,
        чтобы избежать задержки и при этом не читать видео повторно в каждом окне.
        """
        self.current_frame = frame_idx
        if self.seek_update_timer.isActive():
            self.seek_update_timer.stop()
        self._display_current_frame()
        self.frame_changed.emit(self.current_frame)

    def get_cached_pixmap(self, frame_idx: int) -> QPixmap | None:
        """Попытаться получить pixmap кадра из кэша (без декодирования видео)."""
        if self._last_pixmap_frame == frame_idx and self._last_pixmap is not None:
            return self._last_pixmap

        # Ключ кэша совпадает с тем, что используется в _numpy_to_pixmap
        w, h = self.video_service.get_resolution()
        cached = self.frame_cache.get((frame_idx, w, h))
        return cached

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
        print(f"Playback speed changed to: {speed}x")

        # Если видео воспроизводится, перезапустить таймер с новым интервалом
        if self.playing:
            fps = self.video_service.get_fps()
            interval_ms = int(1000 / (fps * self._speed)) if fps > 0 else 33
            self.playback_timer.setInterval(interval_ms)

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

            # Запомнить и разослать другим окнам
            self._last_pixmap = pixmap
            self._last_pixmap_frame = self.current_frame
            self.pixmap_changed.emit(pixmap, self.current_frame)

        except Exception as e:
            print(f"Error displaying frame: {e}")

    def _numpy_to_pixmap(self, frame: np.ndarray) -> QPixmap:
        """Конвертировать numpy array (BGR) в QPixmap с кэшированием и оптимизацией.

        Оптимизация производительности:
        - используем лёгкий ключ кэша (номер кадра + размер),
          вместо вычисления hash(frame.tobytes()), которое
          каждый раз пробегало весь буфер кадра и вызывало
          фризы при перемотке и воспроизведении.
        """
        # Лёгкий ключ кэша: (текущий кадр, ширина, высота)
        h, w, ch = frame.shape
        cache_key = (self.current_frame, w, h)

        # Проверить кэш
        cached = self.frame_cache.get(cache_key)
        if cached is not None:
            return cached

        # Конвертировать BGR в RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w

        # Создать QImage
        qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # Конвертировать в QPixmap
        pixmap = QPixmap.fromImage(qt_image)

        # Оптимизированное масштабирование
        if self.use_high_quality_scaling or self._speed <= 1.0:
            # Использовать высококачественное масштабирование для нормальной скорости
            pixmap = pixmap.scaledToWidth(self.target_width, Qt.TransformationMode.SmoothTransformation)
        else:
            # Для ускоренного воспроизведения использовать быстрое масштабирование
            pixmap = pixmap.scaledToWidth(self.target_width, Qt.TransformationMode.FastTransformation)

        # Сохранить в кэш
        if len(self.frame_cache) >= self.cache_size:
            # Очистить кэш, если он слишком большой
            self.frame_cache.clear()
        self.frame_cache[cache_key] = pixmap

        return pixmap
