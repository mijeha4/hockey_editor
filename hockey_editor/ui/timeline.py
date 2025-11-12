import tkinter as tk
from PIL import ImageTk
from typing import List, Callable
from models.marker import Marker, EventType

class TimelineWidget(tk.Canvas):
    def __init__(self, parent, width=800, height=60):
        super().__init__(parent, width=width, height=height, bg="#222", highlightthickness=0)
        self.width = width
        self.height = height
        self.on_click: Callable[[int], None] = lambda x: None
        self.markers: List[Marker] = []
        self.total_frames = 0
        self.playhead_x = 0
        self.event_colors = {
            EventType.ATTACK: "#FF4444",
            EventType.DEFENSE: "#4444FF",
            EventType.SHIFT: "#44AA44"
        }
        self.bind("<Button-1>", self._on_click)

    def set_data(self, total_frames: int, markers: List[Marker]):
        self.total_frames = total_frames
        self.markers = sorted(markers, key=lambda m: m.frame)
        self.redraw()

    def update_playhead(self, current_frame: int):
        if self.total_frames > 0:
            x = current_frame / self.total_frames * self.winfo_width()
            self.playhead_x = x
            self.redraw_playhead()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.height

        # Превью (упрощённо — будет обновляться из контроллера)
        self.create_rectangle(0, 0, w, h, fill="#333", outline="#555")

        # Маркеры
        for marker in self.markers:
            if self.total_frames > 0:
                x = marker.frame / self.total_frames * w
                color = self.event_colors.get(marker.type, "white")
                self.create_line(x, 0, x, h, fill=color, width=3)
                self.create_text(x, h//2, text="▲", fill=color, font=("Arial", 10, "bold"))

        # Плейхед
        self.playhead_id = self.create_line(0, 0, 0, h, fill="yellow", width=2)

    def redraw_playhead(self):
        self.coords(self.playhead_id, self.playhead_x, 0, self.playhead_x, self.height)

    def _on_click(self, event):
        if self.total_frames > 0:
            frame = int(event.x / self.winfo_width() * self.total_frames)
            self.on_click(frame)