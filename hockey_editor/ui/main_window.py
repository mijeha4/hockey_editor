import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading
import cv2
from utils.time_utils import format_time
from models.marker import Marker, EventType
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

        # Выбор события
        event_frame = tk.Frame(self.root)
        event_frame.pack(pady=5)
        tk.Label(event_frame, text="Событие:").pack(side=tk.LEFT)
        self.event_var = tk.StringVar(value=EventType.ATTACK.value)
        for et in EventType:
            color = self._get_color(et)
            tk.Radiobutton(event_frame, text=et.value, variable=self.event_var,
                           value=et.value, bg=color, fg="white", selectcolor="#333").pack(side=tk.LEFT, padx=5)

        # === Таймлайны для каждого события ===
        self.timeline_frame = tk.Frame(self.root)
        self.timeline_frame.pack(pady=10, fill=tk.X, padx=20)

        self.timelines = {}
        event_types = [EventType.ATTACK, EventType.DEFENSE, EventType.SHIFT]
        colors = ["#FF4444", "#4444FF", "#44AA44"]

        for et, color in zip(event_types, colors):
            frame = tk.Frame(self.timeline_frame)
            frame.pack(fill=tk.X, pady=2)

            label = tk.Label(frame, text=et.value, fg="white", bg=color, font=("Arial", 9, "bold"))
            label.pack(side=tk.LEFT, padx=5)

            canvas = tk.Canvas(frame, height=40, bg="#222", highlightthickness=0)
            canvas.pack(fill=tk.X, expand=True)

            # Сохраняем
            self.timelines[et] = {
                "canvas": canvas,
                "label": label,
                "color": color,
                "playhead_id": None
            }

            # Клик — только на активный
            if et.value == self.event_var.get():
                canvas.bind("<Button-1>", lambda e, t=et: self.controller.on_timeline_click(e, t))
            else:
                canvas.bind("<Button-1>", lambda e: None)

        # Обновление привязок при смене события
        def update_timeline_bindings(*args):
            selected = EventType(self.event_var.get())
            for et, tl in self.timelines.items():
                canvas = tl["canvas"]
                if et == selected:
                    canvas.bind("<Button-1>", lambda e, t=et: self.controller.on_timeline_click(e, t))
                else:
                    canvas.bind("<Button-1>", lambda e: None)

        self.event_var.trace("w", update_timeline_bindings)

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

    def update_all_timelines(self):
        if not self.controller.processor.cap:
            return
        total_frames = self.controller.processor.total_frames
        current_frame = self.controller.current_frame
        markers = self.controller.markers

        for et, tl in self.timelines.items():
            canvas = tl["canvas"]
            canvas.delete("all")
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w <= 1 or h <= 1:
                continue

            # Фон
            canvas.create_rectangle(0, 0, w, h, fill="#333", outline="#555")

            # Отрезки
            for m in markers:
                if m.type != et:
                    continue
                x1 = m.start_frame / total_frames * w
                x2 = m.end_frame / total_frames * w
                if x1 >= w or x2 <= 0:
                    continue

                color = tl["color"]
                # Полупрозрачный: используем светлый оттенок вместо альфа
                light_color = {
                    "#FF4444": "#FF8888",  # светло-красный
                    "#4444FF": "#8888FF",  # светло-синий
                    "#44AA44": "#88CC88",  # светло-зелёный
                }.get(color, "#AAAAAA")

                # Основной прямоугольник — полупрозрачный (светлый)
                canvas.create_rectangle(x1, 0, x2, h, fill=light_color, outline=color, width=2)

                # Надпись
                mid_x = (x1 + x2) / 2
                canvas.create_text(mid_x, h//2, text=m.type.value, fill="black", font=("Arial", 8, "bold"))

            # Плейхед
            if tl["playhead_id"] is None:
                tl["playhead_id"] = canvas.create_line(0, 0, 0, h, fill="yellow", width=2)
            x = current_frame / total_frames * w
            canvas.coords(tl["playhead_id"], x, 0, x, h)

    def update_playhead(self, frame: int):
        self.controller.current_frame = frame
        self.update_all_timelines()

    def on_closing(self):
        self.controller.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()