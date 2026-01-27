import cv2
import numpy as np
import os
from typing import Optional, Tuple


class VideoService:
    """Сервис для работы с видео через OpenCV."""

    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self.video_path: Optional[str] = None
        self.fps: float = 0.0
        self.total_frames: int = 0
        self.frame_width: int = 0
        self.frame_height: int = 0

    def load_video(self, video_path: str) -> bool:
        """Загрузить видеофайл."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        self.cleanup()

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            self.cap = None
            raise RuntimeError(f"Failed to open video: {video_path}")

        self.video_path = video_path
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        return True

    def get_frame(self, frame_index: int) -> np.ndarray:
        """Получить кадр по индексу."""
        if not self.cap:
            raise RuntimeError("No video loaded")

        frame_index = max(0, min(frame_index, self.total_frames - 1))

        # Оптимизация: не дергать cap.set(CAP_PROP_POS_FRAMES) на каждый кадр,
        # если мы и так идём последовательно. Частые установки позиции сильно
        # тормозят воспроизведение и особенно заметны на "тяжёлых" участках.
        try:
            current_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        except Exception:
            current_pos = -1

        # Если запрошенный кадр далеко от текущей позиции — делаем seek.
        # Если рядом (тот же или соседний), читаем последовательно без seek.
        if current_pos < 0 or abs(frame_index - current_pos) > 1:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError(f"Failed to read frame {frame_index}")

        return frame  # numpy array BGR

    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Возвращает текущий кадр без смещения позиции курсора.
        Используется окном предпросмотра для отрисовки.
        """
        if self.cap is None or not self.cap.isOpened():
            print("VideoService: Видео не загружено или ошибка открытия")
            return None

        # 1. Запоминаем текущую позицию
        current_pos = self.cap.get(cv2.CAP_PROP_POS_FRAMES)

        # 2. Принудительно ставим курсор на эту позицию (иногда он сбивается)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

        # 3. Читаем кадр
        ret, frame = self.cap.read()

        # 4. Возвращаем курсор назад (так как read сдвигает его на +1)
        # Это важно, чтобы видео не "дергалось"
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)

        if not ret:
            print(f"VideoService: Не удалось прочитать кадр {current_pos}")
            return None

        return frame

    def get_time_from_frame(self, frame: int) -> float:
        """Конвертировать номер кадра в секунды."""
        if self.fps == 0:
            return 0.0
        return frame / self.fps

    def get_frame_from_time(self, time_sec: float) -> int:
        """Конвертировать секунды в номер кадра."""
        if self.fps == 0:
            return 0
        return int(time_sec * self.fps)

    def get_fps(self) -> float:
        """Получить FPS видео."""
        return self.fps

    def get_total_frames(self) -> int:
        """Получить общее количество кадров."""
        return self.total_frames

    def get_resolution(self) -> Tuple[int, int]:
        """Получить разрешение (width, height)."""
        return self.frame_width, self.frame_height

    def cleanup(self):
        """Закрыть видеофайл."""
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_path = None
        self.fps = 0.0
        self.total_frames = 0
        self.frame_width = 0
        self.frame_height = 0

    def __del__(self):
        self.cleanup()
