import tkinter as tk
import threading
from tkinter import filedialog, messagebox
import cv2
import time
from typing import List, Optional
from utils.time_utils import format_time
from models.marker import Marker, EventType
from .video_processor import VideoProcessor
from .exporter import VideoExporter
from ui.main_window import MainWindow

class VideoController:
    def __init__(self):
        self.processor = VideoProcessor()
        self.markers: List[Marker] = []
        self.current_frame = 0
        self.fps = 30.0
        self.speed = 1.0
        self.view: MainWindow = None
        self.playing = False
        self.playback_thread = None

        # Для создания отрезка
        self.pending_start: Optional[int] = None  # начало отрезка

    def set_view(self, view: MainWindow):
        self.view = view

    def load_video(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv")])
        if not path or not self.processor.load(path):
            return
        self.fps = self.processor.fps
        self.current_frame = 0
        self.markers = []
        self.view.update_markers_list(self.markers)
        self.view.update_all_timelines()
        self.seek_frame(0)

    def play(self):
        if self.playing or not self.processor.cap:
            return
        self.playing = True
        self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
        self.playback_thread.start()

    def pause(self):
        self.playing = False

    def stop(self):
        self.playing = False
        self.processor.release()

    def _playback_loop(self):
        while self.playing and self.processor.cap:
            ret, frame = self.processor.cap.read()
            if not ret:
                self.playing = False
                break
            self.current_frame = int(self.processor.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.view.root.after(0, self.view.update_video_frame, frame)
            self.view.root.after(0, self.view.update_playhead, self.current_frame)
            time.sleep(1 / (self.fps * self.speed))

    def update_speed(self):
        self.speed = self.view.speed_var.get()

    def seek_frame(self, frame: int):
        self.current_frame = max(0, min(frame, self.processor.total_frames - 1))
        if self.playing:
            self.pause()
        self.processor.seek(self.current_frame)
        frame_bgr = self.processor.get_frame(self.current_frame)
        if frame_bgr is not None:
            self.view.root.after(0, self.view.update_video_frame, frame_bgr)
            #self.view.root.after(0, self.view.update_playhead, self.current_frame)
            self.view.root.after(0, self.view.update_all_timelines)

    def remove_selected_marker(self):
        sel = self.view.markers_list.curselection()
        if sel:
            idx = sel[0]
            self.markers.pop(idx)
            self.view.root.after(0, self.view.update_markers_list, self.markers)
            self.view.root.after(0, self.view.update_all_timelines, self.processor.total_frames, self.markers)

    def clear_markers(self):
        if messagebox.askyesno("Очистить", "Удалить все маркеры?"):
            self.markers = []
            self.view.root.after(0, self.view.update_markers_list, self.markers)
            self.view.root.after(0, self.view.update_all_timelines, self.processor.total_frames, self.markers)

    def export_video(self):
        if not self.processor.path or not self.markers:
            messagebox.showerror("Ошибка", "Загрузите видео и добавьте отрезки")
            return
        path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if not path:
            return

        def export():
            try:
                VideoExporter.export(
                    self.processor.path, self.markers,
                    self.processor.total_frames, self.fps, path
                )
                self.view.root.after(0, lambda: messagebox.showinfo("Готово", f"Сохранено:\n{path}"))
            except Exception as e:
                self.view.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))

        threading.Thread(target=export, daemon=True).start()