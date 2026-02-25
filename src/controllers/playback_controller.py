from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Optional

import cv2
import numpy as np

from PySide6.QtCore import QObject, QTimer, Signal, Qt
from PySide6.QtGui import QPixmap, QImage

if TYPE_CHECKING:
    from services.video_engine import VideoService
    from views.widgets.player_controls import PlayerControls


class PlaybackController(QObject):
    """Контроллер управления воспроизведением видео."""

    frame_changed = Signal(int)
    pixmap_changed = Signal(QPixmap, int)  # pixmap, frame_idx

    def __init__(self, video_service: "VideoService", player_controls: "PlayerControls", main_window):
        super().__init__()

        self.video_service = video_service
        self.player_controls = player_controls
        self.main_window = main_window

        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._on_playback_tick)

        self.seek_update_timer = QTimer(self)
        self.seek_update_timer.setSingleShot(True)
        self.seek_update_timer.timeout.connect(self._display_current_frame)

        self.playing = False
        self.current_frame = 0
        self._speed = 1.0

        self._last_pixmap: Optional[QPixmap] = None
        self._last_pixmap_frame: Optional[int] = None

        # LRU cache: key=(frame_idx, target_width, quality_flag) -> QPixmap
        self.cache_size = 100
        self.frame_cache: "OrderedDict[tuple, QPixmap]" = OrderedDict()

        self.target_width = 800
        self.use_high_quality_scaling = False

        self.player_controls.playClicked.connect(self._on_play_clicked)
        self.player_controls.speedChanged.connect(self._on_speed_changed)
        self.player_controls.speedStepChanged.connect(self._on_speed_step_changed)

    # ─── Public API ───

    def load_video(self, video_path: str) -> bool:
        try:
            success = self.video_service.load_video(video_path)
            if not success:
                return False

            total_frames = self.video_service.get_total_frames()
            self.player_controls.set_duration(total_frames)
            self.player_controls.set_current_frame(0)

            self.current_frame = 0
            self._clear_cache()
            self._display_current_frame()

            self.pause()
            self._update_time_display()  # ← ДОБАВИТЬ
            return True
        except Exception as e:
            print(f"Error loading video: {e}")
            return False

    def play(self) -> None:
        if not self.video_service.cap or self.playing:
            return

        self.playing = True
        self._restart_timer_for_speed()

    def pause(self) -> None:
        self.playing = False
        self.playback_timer.stop()

    def toggle_play_pause(self) -> None:
        self.pause() if self.playing else self.play()

    def get_speed(self) -> float:
        return self._speed

    def seek_to_frame(self, frame_idx: int) -> None:
        frame_idx = self._clamp_frame(frame_idx)
        self.current_frame = frame_idx

        if self.seek_update_timer.isActive():
            self.seek_update_timer.stop()
        self.seek_update_timer.start(30)

        self._update_time_display()  # ← ДОБАВИТЬ
        self.frame_changed.emit(self.current_frame)

    def seek_to_frame_immediate(self, frame_idx: int) -> None:
        frame_idx = self._clamp_frame(frame_idx)
        self.current_frame = frame_idx

        if self.seek_update_timer.isActive():
            self.seek_update_timer.stop()

        self._display_current_frame()
        self.frame_changed.emit(self.current_frame)

    def get_cached_pixmap(self, frame_idx: int) -> Optional[QPixmap]:
        if self._last_pixmap_frame == frame_idx and self._last_pixmap is not None:
            return self._last_pixmap

        # Try cache by any quality mode that matches current settings
        key = self._cache_key(frame_idx)
        pix = self.frame_cache.get(key)
        if pix is not None:
            # refresh LRU
            self.frame_cache.move_to_end(key)
        return pix

    # ─── Internals ───

    def _clamp_frame(self, frame_idx: int) -> int:
        total = self.video_service.get_total_frames()
        if total <= 0:
            return 0
        return max(0, min(frame_idx, total - 1))

    def _restart_timer_for_speed(self) -> None:
        fps = self.video_service.get_fps()
        interval_ms = int(1000 / (fps * self._speed)) if fps > 0 else 33
        self.playback_timer.start(max(1, interval_ms))

    def _on_play_clicked(self) -> None:
        self.toggle_play_pause()

    def _on_speed_step_changed(self, step: int) -> None:
        current_speed = self.player_controls.get_current_speed()
        speeds = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0]
        try:
            current_index = speeds.index(current_speed)
            new_index = max(0, min(len(speeds) - 1, current_index + step))
            self.player_controls.set_speed(speeds[new_index])
        except ValueError:
            self.player_controls.set_speed(1.0)

    def _on_speed_changed(self, speed: float) -> None:
        self._speed = speed
        if self.playing:
            self._restart_timer_for_speed()

    def _on_playback_tick(self) -> None:
        if not self.playing:
            return

        self.current_frame = self._clamp_frame(self.current_frame + 1)

        total_frames = self.video_service.get_total_frames()
        if total_frames > 0 and self.current_frame >= total_frames - 1:
            self.pause()

        self.player_controls.set_current_frame(self.current_frame)
        self._display_current_frame()
        self._update_time_display()  # ← ДОБАВИТЬ
        self.frame_changed.emit(self.current_frame)

    def _display_current_frame(self) -> None:
        try:
            frame_idx = self._clamp_frame(self.current_frame)
            self.current_frame = frame_idx

            frame = self.video_service.get_frame(frame_idx)
            if frame is None:
                return

            pixmap = self._numpy_to_pixmap(frame, frame_idx)

            self.main_window.set_video_image(pixmap)

            self._last_pixmap = pixmap
            self._last_pixmap_frame = frame_idx
            self.pixmap_changed.emit(pixmap, frame_idx)

            self._update_time_display()  # ← ДОБАВИТЬ

        except Exception as e:
            print(f"Error displaying frame: {e}")

    def _cache_key(self, frame_idx: int) -> tuple:
        # include scaling params; if you change target_width or quality, cache must differ
        quality = self.use_high_quality_scaling or self._speed <= 1.0
        return (frame_idx, self.target_width, quality)

    def _numpy_to_pixmap(self, frame: np.ndarray, frame_idx: int) -> QPixmap:
        key = self._cache_key(frame_idx)
        cached = self.frame_cache.get(key)
        if cached is not None:
            self.frame_cache.move_to_end(key)
            return cached

        # BGR -> RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w

        # Safe QImage
        image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(image)

        quality_mode = Qt.TransformationMode.SmoothTransformation \
            if (self.use_high_quality_scaling or self._speed <= 1.0) \
            else Qt.TransformationMode.FastTransformation

        pixmap = pixmap.scaledToWidth(self.target_width, quality_mode)

        self._lru_put(key, pixmap)
        return pixmap

    def _lru_put(self, key: tuple, pixmap: QPixmap) -> None:
        self.frame_cache[key] = pixmap
        self.frame_cache.move_to_end(key)
        while len(self.frame_cache) > self.cache_size:
            self.frame_cache.popitem(last=False)

    def _clear_cache(self) -> None:
        self.frame_cache.clear()
        self._last_pixmap = None
        self._last_pixmap_frame = None

    def _update_time_display(self) -> None:
        """Обновить отображение времени в PlayerControls."""
        fps = self.video_service.get_fps()
        total = self.video_service.get_total_frames()
        if fps > 0 and total > 0:
            current_sec = self.current_frame / fps
            total_sec = total / fps
            self.player_controls.update_time_label(current_sec, total_sec)