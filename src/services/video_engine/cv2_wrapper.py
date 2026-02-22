from __future__ import annotations

import os
from typing import Optional, Tuple

import cv2
import numpy as np


class VideoService:
    """Video service wrapper around OpenCV VideoCapture.

    Notes:
    - Not thread-safe. Use one VideoCapture per thread/process.
    - Frames returned are BGR np.ndarray.
    """

    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self.video_path: Optional[str] = None

        self.fps: float = 0.0
        self.total_frames: int = 0
        self.frame_width: int = 0
        self.frame_height: int = 0

        # Internal cursor tracking (next frame index that cap.read() would read)
        self._next_read_index: Optional[int] = None

    # ──────────────────────────────────────────────────────────────────────
    # State
    # ──────────────────────────────────────────────────────────────────────

    @property
    def is_loaded(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def load_video(self, video_path: str) -> bool:
        """Load video file."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        self.cleanup()

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            cap.release()
            raise RuntimeError(f"Failed to open video: {video_path}")

        self.cap = cap
        self.video_path = video_path

        fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 0.0)
        self.fps = fps if fps > 0 else 30.0  # fallback

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        # After open, the next read is typically frame 0
        self._next_read_index = 0

        return True

    # ──────────────────────────────────────────────────────────────────────
    # Frame access
    # ──────────────────────────────────────────────────────────────────────

    def _clamp_frame(self, frame_index: int) -> int:
        if self.total_frames <= 0:
            return max(0, int(frame_index))
        return max(0, min(int(frame_index), self.total_frames - 1))

    def get_frame(self, frame_index: int) -> np.ndarray:
        """Get a frame by index. Raises on errors."""
        frame = self.try_get_frame(frame_index)
        if frame is None:
            raise RuntimeError(f"Failed to read frame {frame_index}")
        return frame

    def try_get_frame(self, frame_index: int) -> Optional[np.ndarray]:
        """Get a frame by index. Returns None on errors."""
        if not self.is_loaded:
            return None

        assert self.cap is not None

        frame_index = self._clamp_frame(frame_index)

        # Fast path: sequential read if we're exactly at expected next index
        if self._next_read_index is not None and frame_index == self._next_read_index:
            ret, frame = self.cap.read()
            if not ret:
                return None
            self._next_read_index = frame_index + 1
            return frame

        # Otherwise do a seek
        ok = self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        # Some backends return False but still seek; we proceed regardless.
        ret, frame = self.cap.read()
        if not ret:
            # after failed read, cursor position is unknown
            self._next_read_index = None
            return None

        self._next_read_index = frame_index + 1
        return frame

    # ──────────────────────────────────────────────────────────────────────
    # Conversions
    # ──────────────────────────────────────────────────────────────────────

    def get_time_from_frame(self, frame: int) -> float:
        return (frame / self.fps) if self.fps > 0 else 0.0

    def get_frame_from_time(self, time_sec: float) -> int:
        return int(time_sec * self.fps) if self.fps > 0 else 0

    # ──────────────────────────────────────────────────────────────────────
    # Info
    # ──────────────────────────────────────────────────────────────────────

    def get_fps(self) -> float:
        return self.fps

    def get_total_frames(self) -> int:
        return self.total_frames

    def get_resolution(self) -> Tuple[int, int]:
        """(width, height)"""
        return self.frame_width, self.frame_height

    # ──────────────────────────────────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────────────────────────────────

    def cleanup(self) -> None:
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        self.video_path = None
        self.fps = 0.0
        self.total_frames = 0
        self.frame_width = 0
        self.frame_height = 0
        self._next_read_index = None

    def __del__(self):
        self.cleanup()