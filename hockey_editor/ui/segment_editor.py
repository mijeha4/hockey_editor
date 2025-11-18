# ui/segment_editor.py
import tkinter as tk
from tkinter import messagebox
from models.marker import Marker, EventType
from utils.time_utils import format_time


class SegmentEditor:
    def __init__(self, parent, controller, event_type: EventType, on_save, on_update_markers_list, on_update_all_timelines):
        self.controller = controller
        self.event_type = event_type
        self.on_save = on_save  # Сохранение навсегда
        self.on_update_markers_list = on_update_markers_list
        self.on_update_all_timelines = on_update_all_timelines
        self.parent = parent

        self.window = tk.Toplevel(parent)
        self.window.title(f"Редактирование: {event_type.value}")
        self.window.geometry("800x220")
        self.window.transient(parent)
        self.window.grab_set()

        self.setup_ui()

    def setup_ui(self):
        # === ТАЙМЛАЙН ПРЕДПРОСМОТРА ===
        self.canvas = tk.Canvas(self.window, height=80, bg="#222", highlightthickness=0)
        self.canvas.pack(fill=tk.X, padx=10, pady=10)

        # === ПОЛЗУНКИ ===
        ctrl_frame = tk.Frame(self.window)
        ctrl_frame.pack(pady=5)

        tk.Label(ctrl_frame, text="Начало:").grid(row=0, column=0, padx=5)
        self.start_var = tk.DoubleVar()
        self.start_scale = tk.Scale(
            ctrl_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.start_var,
            command=lambda v: self.update_preview()
        )
        self.start_scale.grid(row=0, column=1, sticky="ew")

        tk.Label(ctrl_frame, text="Конец:").grid(row=1, column=0, padx=5)
        self.end_var = tk.DoubleVar(value=100)
        self.end_scale = tk.Scale(
            ctrl_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.end_var,
            command=lambda v: self.update_preview()
        )
        self.end_scale.grid(row=1, column=1, sticky="ew")

        ctrl_frame.columnconfigure(1, weight=1)

        # === КНОПКИ ===
        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Сохранить", command=self.save_and_transfer,
                  bg="#4CAF50", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=self.window.destroy,
                  bg="#F44336", fg="white").pack(side=tk.LEFT, padx=5)

        # === ИНИЦИАЛИЗАЦИЯ ===
        self.total_frames = self.controller.processor.total_frames
        self.update_preview()

    def update_preview(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            self.window.after(100, self.update_preview)
            return

        # Фон
        self.canvas.create_rectangle(0, 0, w, h, fill="#333", outline="#555")

        # Отрезок
        start_pct = self.start_var.get() / 100
        end_pct = self.end_var.get() / 100
        x1 = start_pct * w
        x2 = end_pct * w

        color = {
            EventType.ATTACK: "#FF4444",
            EventType.DEFENSE: "#4444FF",
            EventType.SHIFT: "#44AA44"
        }[self.event_type]

        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        light_color = f"#{min(255, r+100):02x}{min(255, g+100):02x}{min(255, b+100):02x}"

        self.canvas.create_rectangle(x1, 0, x2, h, fill=light_color, outline=color, width=2)
        mid_x = (x1 + x2) / 2
        self.canvas.create_text(mid_x, h//2, text=self.event_type.value, fill="black", font=("Arial", 10, "bold"))

        # Время
        start_sec = start_pct * self.total_frames / self.controller.fps
        end_sec = end_pct * self.total_frames / self.controller.fps
        self.canvas.create_text(w//2, h-10, text=f"{format_time(start_sec)} – {format_time(end_sec)}", fill="white")

    def save_and_transfer(self):
        """Переносит и сохраняет отрезок на основной таймлайн"""
        start_pct = self.start_var.get() / 100
        end_pct = self.end_var.get() / 100
        if end_pct <= start_pct:
            messagebox.showwarning("Ошибка", "Конец должен быть позже начала")
            return
        start_frame = int(start_pct * self.total_frames)
        end_frame = int(end_pct * self.total_frames)

        marker = Marker(start_frame=start_frame, end_frame=end_frame, type=self.event_type)

        # Сохраняем маркер
        self.on_save(marker)
        self.window.destroy()

    def save(self):
        """Сохраняет отрезок навсегда"""
        start_pct = self.start_var.get() / 100
        end_pct = self.end_var.get() / 100
        if end_pct <= start_pct:
            messagebox.showerror("Ошибка", "Конец должен быть позже начала")
            return

        start_frame = int(start_pct * self.total_frames)
        end_frame = int(end_pct * self.total_frames)

        marker = Marker(start_frame=start_frame, end_frame=end_frame, type=self.event_type)
        self.on_save(marker)  # Вызываем callback из main_window
        self.window.destroy()
