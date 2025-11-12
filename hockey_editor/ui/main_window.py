import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading

import cv2
from .timeline import TimelineWidget
from models.marker import Marker, EventType
from utils.time_utils import format_time

class MainWindow:
    def __init__(self, controller):
        self.controller = controller
        self.root = tk.Tk()
        self.root.title("Хоккейный видеомонтажёр")
        self.root.geometry("900x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.setup_ui()
        self.playback_thread = None

    def setup_ui(self):
        # Видео
        self.video_label = tk.Label(self.root, bg="black")
        self.video_label.pack(pady=10, fill=tk.X, padx=20)

        # Кнопки
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(pady=5)
        tk.Button(ctrl_frame, text="Открыть видео", command=self.controller.load_video).pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl_frame, text="Экспорт", command=self.controller.export_video, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)

        # Выбор события
        event_frame = tk.Frame(self.root)
        event_frame.pack(pady=5)
        tk.Label(event_frame, text="Событие:").pack(side=tk.LEFT)
        self.event_var = tk.StringVar(value=EventType.ATTACK.value)
        for et in EventType:
            color = self._get_color(et)
            tk.Radiobutton(event_frame, text=et.value, variable=self.event_var,
                           value=et.value, bg=color, fg="white", selectcolor="#333").pack(side=tk.LEFT, padx=5)

        # Таймлайн
        self.timeline = TimelineWidget(self.root, height=60)
        self.timeline.pack(pady=10, fill=tk.X, padx=20)
        self.timeline.on_click = self.controller.add_marker_at_frame

        # Список маркеров
        list_frame = tk.Frame(self.root)
        list_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)
        tk.Label(list_frame, text="Маркеры:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.markers_list = tk.Listbox(list_frame, height=8)
        self.markers_list.pack(fill=tk.BOTH, expand=True, pady=5)

        btn_frame = tk.Frame(list_frame)
        btn_frame.pack()
        tk.Button(btn_frame, text="Удалить", command=self.controller.remove_selected_marker).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Очистить", command=self.controller.clear_markers).pack(side=tk.LEFT, padx=5)

    def _get_color(self, event_type: EventType) -> str:
        colors = {EventType.ATTACK: "#FF4444", EventType.DEFENSE: "#4444FF", EventType.SHIFT: "#44AA44"}
        return colors.get(event_type, "gray")

    def update_video_frame(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (800, 450))
        img = Image.fromarray(frame)
        photo = ImageTk.PhotoImage(img)
        self.video_label.config(image=photo)
        self.video_label.image = photo

    def update_markers_list(self, markers: list):
        self.markers_list.delete(0, tk.END)
        for i, m in enumerate(markers):
            time_str = format_time(m.frame / self.controller.fps)
            self.markers_list.insert(tk.END, f"{i+1}. [{time_str}] {m.type.value}")
            self.markers_list.itemconfig(i, fg=self._get_color(m.type))

    def update_timeline(self, total_frames: int, markers: list):
        self.timeline.set_data(total_frames, markers)

    def update_playhead(self, frame: int):
        self.timeline.update_playhead(frame)

    def start_playback(self):
        if self.playback_thread and self.playback_thread.is_alive():
            return
        self.playback_thread = threading.Thread(target=self.controller.play_video, daemon=True)
        self.playback_thread.start()

    def on_closing(self):
        self.controller.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()