import cv2
import numpy as np
from typing import Optional, Tuple
import os


class VideoProcessor:
    """Управление видео через OpenCV (cv2.VideoCapture) с буферизацией текущего кадра."""

    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self.video_path: Optional[str] = None
        self.fps: float = 0.0
        self.total_frames: int = 0
        self.current_frame_idx: int = 0
        self.frame_width: int = 0
        self.frame_height: int = 0
        self._current_frame_buffer: Optional[np.ndarray] = None  # Буфер текущего кадра

    def load(self, video_path: str) -> bool:
        """Загрузить видеофайл."""
        if not os.path.exists(video_path):
            return False
        
        # Закрыть предыдущее видео
        self.cleanup()
        
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            self.cap = None
            return False
        
        self.video_path = video_path
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.current_frame_idx = 0
        
        # Загрузить первый кадр в буфер
        self._read_and_buffer_frame()
        
        return True

    def seek(self, frame_idx: int) -> bool:
        """Перемотать на кадр (БЕЗ воспроизведения)."""
        if not self.cap:
            return False
        
        frame_idx = max(0, min(frame_idx, self.total_frames - 1))
        ret = self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        if ret:
            self.current_frame_idx = frame_idx
            self._read_and_buffer_frame()
        return ret

    def advance_frame(self) -> bool:
        """Перейти на следующий кадр (для воспроизведения)."""
        if not self.cap:
            return False
        
        # Просто читаем следующий кадр
        ret, frame = self.cap.read()
        if ret:
            self.current_frame_idx = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self._current_frame_buffer = frame
            return True
        return False

    def _read_and_buffer_frame(self) -> bool:
        """Прочитать кадр с текущей позиции и сохранить в буфер."""
        if not self.cap:
            return False
        
        ret, frame = self.cap.read()
        if ret:
            self._current_frame_buffer = frame
            return True
        return False

    def get_current_frame(self) -> Optional[np.ndarray]:
        """Получить текущий кадр из буфера (БЕЗ чтения)."""
        return self._current_frame_buffer

    def get_frame_at(self, frame_idx: int) -> Optional[np.ndarray]:
        """Получить кадр по индексу (вспомогательный метод)."""
        if not self.cap:
            return None
        
        self.seek(frame_idx)
        return self.get_current_frame()

    def get_current_time(self) -> float:
        """Получить текущее время (секунды)."""
        if self.fps == 0:
            return 0.0
        return self.current_frame_idx / self.fps

    def get_fps(self) -> float:
        """Получить FPS видео."""
        return self.fps

    def get_total_frames(self) -> int:
        """Получить общее количество кадров."""
        return self.total_frames

    def get_total_time(self) -> float:
        """Получить общую длину видео (секунды)."""
        if self.fps == 0:
            return 0.0
        return self.total_frames / self.fps

    def get_current_frame_idx(self) -> int:
        """Получить индекс текущего кадра."""
        return self.current_frame_idx

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
        self.current_frame_idx = 0
        self._current_frame_buffer = None

    def __del__(self):
        self.cleanup()

