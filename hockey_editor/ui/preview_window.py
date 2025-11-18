import tkinter as tk
from tkinter import messagebox
from typing import List
from models.marker import Marker, EventType
from PIL import Image, ImageTk
import cv2
import threading
import time

class PreviewWindow:
    def __init__(self, parent, controller, markers: List[Marker]):
        self.controller = controller
        self.markers = markers
        self.parent = parent
        self.playing = False
        self.current_frame = 0
        self.selected_markers = []

        self.window = tk.Toplevel(parent)
        self.window.title("Предпросмотр событий")
        self.window.geometry("1000x600")
        self.window.transient(parent)
        self.window.grab_set()

        self.setup_ui()

    def setup_ui(self):
        # Video display
        self.video_label = tk.Label(self.window, bg="black")
        self.video_label.pack(pady=10, fill=tk.X, padx=20)

        # Event selection
        self.event_frame = tk.Frame(self.window)
        self.event_frame.pack(pady=10, fill=tk.X, padx=20)

        tk.Label(self.event_frame, text="Выберите события:").pack(anchor=tk.W)

        self.event_vars = {}
        for et in EventType:
            var = tk.BooleanVar(value=True)
            self.event_vars[et] = var
            cb = tk.Checkbutton(self.event_frame, text=et.value, variable=var,
                              command=self.update_selected_markers)
            cb.pack(anchor=tk.W)

        # Controls
        ctrl_frame = tk.Frame(self.window)
        ctrl_frame.pack(pady=5)

        self.play_btn = tk.Button(ctrl_frame, text="Play", command=self.toggle_play)
        self.play_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(ctrl_frame, text="Экспорт", command=self.export_selected,
                 bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=10)

        # Update selected markers initially
        self.update_selected_markers()

    def update_selected_markers(self):
        self.selected_markers = []
        for et, var in self.event_vars.items():
            if var.get():
                self.selected_markers.extend(
                    [m for m in self.markers if m.type == et]
                )
        self.selected_markers.sort(key=lambda m: m.start_frame)

    def toggle_play(self):
        if self.playing:
            self.playing = False
            self.play_btn.config(text="Play")
        else:
            self.playing = True
            self.play_btn.config(text="Pause")
            threading.Thread(target=self._playback_loop, daemon=True).start()

    def _playback_loop(self):
        while self.playing:
            if not self.selected_markers:
                self.playing = False
                break

            # Find the current segment
            current_segment = None
            for marker in self.selected_markers:
                if marker.start_frame <= self.current_frame <= marker.end_frame:
                    current_segment = marker
                    break

            if not current_segment:
                # Move to next segment
                for i, marker in enumerate(self.selected_markers):
                    if marker.start_frame > self.current_frame:
                        self.current_frame = marker.start_frame
                        current_segment = marker
                        break
                else:
                    # Reached end
                    self.playing = False
                    break

            # Play the current segment
            if self.current_frame <= current_segment.end_frame:
                frame = self.controller.processor.get_frame(self.current_frame)
                if frame is not None:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame = cv2.resize(frame, (800, 450))
                    img = Image.fromarray(frame)
                    photo = ImageTk.PhotoImage(img)
                    self.video_label.config(image=photo)
                    self.video_label.image = photo

                self.current_frame += 1
                time.sleep(1 / self.controller.fps)
            else:
                # Move to next segment
                self.current_frame += 1

    def export_selected(self):
        if not self.selected_markers:
            messagebox.showwarning("Нет событий", "Выберите хотя бы одно событие")
            return

        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if not path:
            return

        def export():
            try:
                from core.exporter import VideoExporter
                VideoExporter.export(
                    self.controller.processor.path,
                    self.selected_markers,
                    self.controller.processor.total_frames,
                    self.controller.fps,
                    path
                )
                self.window.after(0, lambda: messagebox.showinfo("Готово", f"Сохранено:\n{path}"))
            except Exception as e:
                self.window.after(0, lambda: messagebox.showerror("Ошибка", str(e)))

        threading.Thread(target=export, daemon=True).start()
