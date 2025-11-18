# ui/main_window.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu
from PIL import Image, ImageTk
import threading
import cv2
import json
import os
from models.marker import Marker, EventType
from utils.time_utils import format_time
from .segment_editor import SegmentEditor  # ← относительный импорт
from .timeline import TimelineWidget


class MainWindow:
    def __init__(self, controller):
        self.controller = controller
        self.root = tk.Tk()
        self.root.title("Хоккейный видеомонтажёр")
        self.root.geometry("900x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.playing = False
        self.setup_ui()

    def setup_ui(self):
        # Создаем меню
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Сохранить проект", command=self.save_project)
        file_menu.add_command(label="Открыть проект", command=self.open_project)
        file_menu.add_command(label="Новый проект", command=self.new_project)

        # Видео
        self.video_label = tk.Label(self.root, bg="black")
        self.video_label.pack(pady=10, fill=tk.X, padx=20)

        # Кнопки управления
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(pady=5)

        tk.Button(ctrl_frame, text="Открыть", command=self.controller.load_video).pack(side=tk.LEFT, padx=5)
        self.play_btn = tk.Button(ctrl_frame, text="Play", command=self.toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=5)

        # Скорость
        tk.Label(ctrl_frame, text="Скорость:").pack(side=tk.LEFT, padx=5)
        self.speed_var = tk.DoubleVar(value=1.0)
        for speed in [0.5, 1.0, 2.0]:
            tk.Radiobutton(ctrl_frame, text=f"{speed}x", variable=self.speed_var, value=speed,
                           command=self.controller.update_speed).pack(side=tk.LEFT)

        tk.Button(ctrl_frame, text="Экспорт", command=self.controller.export_video,
                  bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=10)

        tk.Button(ctrl_frame, text="Предпросмотр", command=self.open_preview_window,
                  bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=10)

        # === КНОПКИ СОБЫТИЙ ===
        event_frame = tk.Frame(self.root)
        event_frame.pack(pady=5)

        self.event_buttons = {}
        for et in EventType:
            color = {
                EventType.ATTACK: "#FF4444",
                EventType.DEFENSE: "#4444FF",
                EventType.SHIFT: "#44AA44"
            }[et]
            btn = tk.Button(event_frame, text=et.value, bg=color, fg="white",
                            command=lambda t=et: self.open_segment_editor(t))
            btn.pack(side=tk.LEFT, padx=5)
            self.event_buttons[et] = btn

        # === ТАЙМЛАЙНЫ (с использованием TimelineWidget) ===
        self.timeline_frame = tk.Frame(self.root)
        self.timeline_frame.pack(pady=10, fill=tk.X, padx=20)

        self.timelines = {}
        event_types = [EventType.ATTACK, EventType.DEFENSE, EventType.SHIFT]

        for et in event_types:
            frame = tk.Frame(self.timeline_frame)
            frame.pack(fill=tk.X, pady=2)

            label = tk.Label(frame, text=et.value, fg="white", bg={
                EventType.ATTACK: "#FF4444",
                EventType.DEFENSE: "#4444FF",
                EventType.SHIFT: "#44AA44"
            }[et], font=("Arial", 9, "bold"))
            label.pack(side=tk.LEFT, padx=5)

            timeline_widget = TimelineWidget(frame, width=800, height=40, event_type=et)
            timeline_widget.on_click = lambda frame, pause_if_playing: self.controller.seek_frame(frame, pause_if_playing)
            timeline_widget.pack(fill=tk.X, expand=True)

            self.timelines[et] = {
                "widget": timeline_widget,
                "label": label,
                "dragging": False,
                "drag_start": None,
                "drag_marker": None
            }

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

    def toggle_play(self):
        if self.playing:
            self.controller.pause()
            self.play_btn.config(text="Play")
        else:
            self.controller.play()
            self.play_btn.config(text="Pause")
        self.playing = not self.playing

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
            start = format_time(m.start_frame / self.controller.fps)
            end = format_time(m.end_frame / self.controller.fps)
            self.markers_list.insert(tk.END, f"{i+1}. {m.type.value} ({start} – {end})")
            color = {
                EventType.ATTACK: "#FF4444",
                EventType.DEFENSE: "#4444FF",
                EventType.SHIFT: "#44AA44"
            }.get(m.type, "gray")
            self.markers_list.itemconfig(i, fg=color)
        self.controller.markers = markers

    def update_all_timelines(self):
        if not self.controller.processor.cap:
            return

        total_frames = self.controller.processor.total_frames
        current_frame = self.controller.current_frame
        markers = self.controller.markers

        for et, tl in self.timelines.items():
            timeline_widget = tl["widget"]
            timeline_widget.set_data(total_frames, markers)
            timeline_widget.update_playhead(current_frame)

    def open_segment_editor(self, event_type: EventType):
        if not self.controller.processor.cap:
            messagebox.showwarning("Нет видео", "Сначала загрузите видео")
            return

        def on_save(marker):
            self.controller.markers.append(marker)
            self.controller.markers.sort(key=lambda m: m.start_frame)
            self.update_markers_list(self.controller.markers)
            self.update_all_timelines()

        SegmentEditor(self.root, self.controller, event_type, on_save, self.update_markers_list, self.update_all_timelines)

    def on_timeline_press(self, event, event_type):
        tl = self.timelines[event_type]
        timeline_widget = tl["widget"]
        x = event.x
        total_frames = self.controller.processor.total_frames
        frame = int(x / timeline_widget.winfo_width() * total_frames)

        for marker in self.controller.markers:
            if marker.type == event_type and marker.start_frame <= frame <= marker.end_frame:
                tl["dragging"] = True
                tl["drag_start"] = x
                tl["drag_marker"] = marker
                break

    def on_timeline_drag(self, event, event_type):
        tl = self.timelines[event_type]
        if tl["dragging"]:
            timeline_widget = tl["widget"]
            x = event.x
            total_frames = self.controller.processor.total_frames
            frame = int(x / timeline_widget.winfo_width() * total_frames)
            marker = tl["drag_marker"]

            if marker:
                duration = marker.end_frame - marker.start_frame
                marker.start_frame = frame
                marker.end_frame = frame + duration
                self.update_all_timelines()

    def on_timeline_release(self, event, event_type):
        tl = self.timelines[event_type]
        tl["dragging"] = False
        tl["drag_start"] = None
        tl["drag_marker"] = None

    def open_preview_window(self):
        if not self.controller.processor.cap:
            messagebox.showwarning("Нет видео", "Сначала загрузите видео")
            return

        from .preview_window import PreviewWindow
        PreviewWindow(self.root, self.controller, self.controller.markers)

    def save_project(self):
        if not self.controller.markers:
            messagebox.showwarning("Нет данных", "Нет маркеров для сохранения")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not file_path:
            return

        project_data = {
            "markers": [
                {
                    "type": marker.type.value,
                    "start_frame": marker.start_frame,
                    "end_frame": marker.end_frame
                }
                for marker in self.controller.markers
            ]
        }

        with open(file_path, "w") as f:
            json.dump(project_data, f, indent=4)

        messagebox.showinfo("Сохранено", f"Проект сохранен в {file_path}")

    def open_project(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            with open(file_path, "r") as f:
                project_data = json.load(f)

            self.controller.markers = []
            for marker_data in project_data.get("markers", []):
                marker = Marker(
                    type=EventType(marker_data["type"]),
                    start_frame=marker_data["start_frame"],
                    end_frame=marker_data["end_frame"]
                )
                self.controller.markers.append(marker)

            self.update_markers_list(self.controller.markers)
            self.update_all_timelines()
            messagebox.showinfo("Открыто", f"Проект загружен из {file_path}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть проект: {str(e)}")

    def new_project(self):
        if messagebox.askokcancel("Новый проект", "Создать новый проект? Несохраненные данные будут потеряны."):
            self.controller.markers = []
            self.update_markers_list(self.controller.markers)
            self.update_all_timelines()
            messagebox.showinfo("Новый проект", "Создан новый проект")

    def on_closing(self):
            if messagebox.askokcancel("Выход", "Закрыть приложение?"):
                self.controller.stop()
                self.root.destroy()

    def run(self):
        self.root.mainloop()
