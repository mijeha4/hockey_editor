"""
VideoReaderThread - многопоточное чтение видеокадров.
Читает кадры в отдельном потоке, главный поток свободен для UI.
"""

import cv2
import numpy as np
from queue import Queue, Empty
from typing import Optional
from PySide6.QtCore import QThread, Signal


class VideoReaderThread(QThread):
    """
    Поток для параллельного чтения видеокадров.
    Использует очередь для передачи кадров в главный поток.
    """
    
    # Сигналы
    frame_decoded = Signal(int, object)  # frame_number, np.ndarray
    error_occurred = Signal(str)          # error_message
    stopped = Signal()                    # поток остановлен
    
    def __init__(self, video_path: str, fps: float, queue_size: int = 5):
        super().__init__()
        self.video_path = video_path
        self.fps = fps
        self.queue_size = queue_size
        self.frame_queue = Queue(maxsize=queue_size)
        
        self.is_running = False
        self.is_paused = False
        self.target_frame = None  # Если не None, перемотать на этот кадр
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.current_frame_number = 0

    def run(self):
        """Главный цикл потока: читает и кладёт кадры в очередь."""
        try:
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                self.error_occurred.emit(f"Cannot open video: {self.video_path}")
                return
            
            self.is_running = True
            frame_delay = int(1000 / self.fps) if self.fps > 0 else 33  # мс
            
            while self.is_running:
                # Проверка на перемотку (seek)
                if self.target_frame is not None:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.target_frame)
                    self.current_frame_number = self.target_frame
                    self.target_frame = None
                
                # Если паузирован, спать
                if self.is_paused:
                    self.msleep(100)
                    continue
                
                # Читать кадр
                ret, frame = self.cap.read()
                if ret:
                    try:
                        self.frame_queue.put_nowait((self.current_frame_number, frame))
                        self.frame_decoded.emit(self.current_frame_number, frame)
                        self.current_frame_number += 1
                    except:
                        pass  # Очередь переполнена, пропустить кадр
                    
                    self.msleep(frame_delay)
                else:
                    # Конец видео
                    self.is_running = False
        
        except Exception as e:
            self.error_occurred.emit(str(e))
        
        finally:
            if self.cap:
                self.cap.release()
            self.stopped.emit()

    def stop(self):
        """Остановить поток."""
        self.is_running = False
        self.wait()

    def pause(self):
        """Пауза (поток продолжает работать, но не читает кадры)."""
        self.is_paused = True

    def resume(self):
        """Возобновить воспроизведение."""
        self.is_paused = False

    def seek(self, frame_number: int):
        """Перемотать на кадр (выполнится в следующей итерации цикла)."""
        self.target_frame = frame_number

    def clear_queue(self):
        """Очистить очередь кадров."""
        try:
            while not self.frame_queue.empty():
                self.frame_queue.get_nowait()
        except Empty:
            pass
