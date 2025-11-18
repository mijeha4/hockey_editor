import tkinter as tk
from PIL import ImageTk
from typing import List, Callable
from models.marker import Marker, EventType

class TimelineWidget(tk.Canvas):
    def __init__(self, parent, width=800, height=60, event_type=None):
        super().__init__(parent, width=width, height=height, bg="#222", highlightthickness=0)
        self.on_click: Callable[[int], None] = lambda x: None
        self.markers: List[Marker] = []
        self.total_frames = 0
        self.playhead_x = 0
        self.event_type = event_type
        self.event_colors = {
            EventType.ATTACK: "#FF4444",
            EventType.DEFENSE: "#4444FF",
            EventType.SHIFT: "#44AA44"
        }
        self.bind("<Button-1>", self._on_click)
        self.playhead_id = None
        self.segment_rects = []

    def set_data(self, total_frames: int, markers: List[Marker]):
        self.total_frames = total_frames
        self.markers = sorted(markers, key=lambda m: m.start_frame)
        self.redraw()

    def update_playhead(self, current_frame: int):
        if self.total_frames > 0 and self.winfo_width() > 1:
            x = current_frame / self.total_frames * self.winfo_width()
            self.playhead_x = x
            self.redraw_playhead()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()  # ← ДИНАМИЧЕСКАЯ ВЫСОТА!

        if w <= 1 or h <= 1:
            return

        self.create_rectangle(0, 0, w, h, fill="#333", outline="#555")

        # === ОТРЕЗКИ ===
        self.segment_rects = []
        for marker in self.markers:
            if self.total_frames <= 0:
                continue
            # Filter markers by event type
            if self.event_type is not None and marker.type != self.event_type:
                continue

            x1 = marker.start_frame / self.total_frames * w
            x2 = marker.end_frame / self.total_frames * w
            if x1 >= w or x2 <= 0:
                continue
            color = self.event_colors.get(marker.type, "white")

            rect = self.create_rectangle(x1, 0, x2, h, fill=color, outline=color, width=2)
            self.segment_rects.append(rect)

            mid_x = (x1 + x2) / 2
            self.create_text(mid_x, h//2, text=marker.type.value, fill="white", font=("Arial", 8, "bold"))

        # === ПЛЕЙХЕД ===
        self.playhead_id = self.create_line(0, 0, 0, h, fill="yellow", width=2)

    def redraw_playhead(self):
        if self.playhead_id:
            h = self.winfo_height()  # ← ДИНАМИЧЕСКАЯ!
            self.coords(self.playhead_id, self.playhead_x, 0, self.playhead_x, h)

    def _on_click(self, event):
        if self.total_frames > 0 and self.winfo_width() > 1:
            frame = int(event.x / self.winfo_width() * self.total_frames)

            # Check if click is on a segment
            for marker in self.markers:
                if self.event_type is not None and marker.type != self.event_type:
                    continue

                x1 = marker.start_frame / self.total_frames * self.winfo_width()
                x2 = marker.end_frame / self.total_frames * self.winfo_width()

                if x1 <= event.x <= x2:
                    self.on_click(marker.start_frame, pause_if_playing=False)
                    return

            # If not on a segment, seek to clicked position
            self.on_click(frame, pause_if_playing=False)
