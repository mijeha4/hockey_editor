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
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError(f"Failed to read frame {frame_index}")

        return frame  # numpy array BGR

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
