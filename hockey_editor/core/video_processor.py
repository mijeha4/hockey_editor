import cv2
import numpy as np
from PIL import Image
from typing import Optional

class VideoProcessor:
    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self.path: Optional[str] = None
        self.total_frames = 0
        self.fps = 30.0
        self.frame_cache = {}

    def load(self, path: str) -> bool:
        self.path = path
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            return False
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.frame_cache.clear()
        return True

    def get_frame(self, frame_num: int) -> Optional[np.ndarray]:
        if frame_num in self.frame_cache:
            return self.frame_cache[frame_num]
        if not self.cap:
            return None
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        if ret:
            self.frame_cache[frame_num] = frame
            return frame
        return None

    def get_thumbnail(self, frame_num: int, size=(20, 15)) -> Optional[Image.Image]:
        frame = self.get_frame(frame_num)
        if frame is None:
            return None
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, size)
        return Image.fromarray(frame)

    def seek(self, frame_num: int):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)

    def release(self):
        if self.cap:
            self.cap.release()
        self.cap = None