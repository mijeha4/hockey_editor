import threading
from tkinter import filedialog, messagebox
import cv2
from typing import List
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
        self.view: MainWindow = None
        self.playing = False

    def set_view(self, view: MainWindow):
        self.view = view

    def load_video(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv")])
        if not path or not self.processor.load(path):
            return
        self.fps = self.processor.fps
        self.markers = []
        self.view.update_markers_list(self.markers)
        self.view.update_timeline(self.processor.total_frames, self.markers)
        self.view.start_playback()

    def play_video(self):
        self.playing = True
        while self.playing and self.processor.cap:
            ret, frame = self.processor.cap.read()
            if not ret:
                break
            self.current_frame = int(self.processor.cap.get(cv2.CAP_PROP_POS_FRAMES))
            self.view.update_video_frame(frame)
            self.view.update_playhead(self.current_frame)
            cv2.waitKey(int(1000 / self.fps))
        self.playing = False

    def add_marker_at_frame(self, frame: int):
        event_str = self.view.event_var.get()
        event_type = EventType(event_str)
        marker = Marker(frame=frame, type=event_type)
        self.markers.append(marker)
        self.markers.sort(key=lambda m: m.frame)
        self.view.update_markers_list(self.markers)
        self.view.update_timeline(self.processor.total_frames, self.markers)
        self.processor.cap.set(cv2.CAP_PROP_POS_FRAMES, frame)

    def remove_selected_marker(self):
        sel = self.view.markers_list.curselection()
        if sel:
            idx = sel[0]
            self.markers.pop(idx)
            self.view.update_markers_list(self.markers)
            self.view.update_timeline(self.processor.total_frames, self.markers)

    def clear_markers(self):
        if messagebox.askyesno("Очистить", "Удалить все маркеры?"):
            self.markers = []
            self.view.update_markers_list(self.markers)
            self.view.update_timeline(self.processor.total_frames, self.markers)

    def export_video(self):
        if not self.processor.path or not self.markers:
            messagebox.showerror("Ошибка", "Загрузите видео и добавьте маркеры")
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

    def stop(self):
        self.playing = False
        self.processor.release()