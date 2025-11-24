from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QImage, QPixmap, QColor, QPainter, QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton,
    QLineEdit, QSpinBox, QWidget
)
import cv2
import numpy as np


class SegmentEditorDialog(QDialog):
    """Окно редактирования отрезка с видео и таймлайном."""

    def __init__(self, controller, marker_idx: int, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.marker_idx = marker_idx
        self.marker = controller.markers[marker_idx]
        self.original_marker = marker_idx  # Сохранить оригинал
        
        # Временные переменные
        self.start_frame = self.marker.start_frame
        self.end_frame = self.marker.end_frame
        
        self.setWindowTitle(f"Edit Segment - {self.marker.type.name}")
        self.setGeometry(100, 100, 1200, 700)
        self.setup_ui()
        self.update_video_frame()

    def setup_ui(self):
        """Создать UI."""
        layout = QVBoxLayout()
        
        # Видео плеер (вверху)
        video_layout = QHBoxLayout()
        self.video_label = QLabel()
        self.video_label.setMinimumSize(600, 400)
        self.video_label.setStyleSheet("background-color: black; border: 1px solid grey;")
        video_layout.addWidget(self.video_label)
        
        # Контролы справа
        controls_layout = QVBoxLayout()
        
        # Текущий фрейм
        fps = self.controller.get_fps()
        current_sec = self.controller.get_current_frame_idx() / fps if fps > 0 else 0
        
        controls_layout.addWidget(QLabel(f"Marker: {self.marker.type.name}"))
        controls_layout.addWidget(QLabel(f"FPS: {fps:.1f}"))
        
        # Время начала
        controls_layout.addWidget(QLabel("Start Time (MM:SS.FF):"))
        self.start_time_edit = QLineEdit(self._format_time(self.start_frame))
        controls_layout.addWidget(self.start_time_edit)
        self.start_time_edit.textChanged.connect(self._on_start_time_changed)
        
        # Время конца
        controls_layout.addWidget(QLabel("End Time (MM:SS.FF):"))
        self.end_time_edit = QLineEdit(self._format_time(self.end_frame))
        controls_layout.addWidget(self.end_time_edit)
        self.end_time_edit.textChanged.connect(self._on_end_time_changed)
        
        # Длина отрезка
        duration = self.end_frame - self.start_frame
        duration_sec = duration / fps if fps > 0 else 0
        controls_layout.addWidget(QLabel(f"Duration: {duration_sec:.2f} sec ({duration} frames)"))
        
        controls_layout.addStretch()
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        apply_btn = QPushButton("✓ Apply")
        apply_btn.clicked.connect(self.apply_changes)
        button_layout.addWidget(apply_btn)
        
        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(self.delete_marker)
        button_layout.addWidget(delete_btn)
        
        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        controls_layout.addLayout(button_layout)
        
        video_layout.addLayout(controls_layout)
        layout.addLayout(video_layout)
        
        # Таймлайн внизу
        self.timeline_label = QLabel()
        self.timeline_label.setMinimumHeight(100)
        self.timeline_label.setStyleSheet("background-color: #1a1a1a; border: 1px solid grey;")
        layout.addWidget(QLabel("Timeline:"))
        layout.addWidget(self.timeline_label)
        
        # Слайдеры для начала и конца
        slider_layout = QHBoxLayout()
        
        slider_layout.addWidget(QLabel("Start:"))
        self.start_slider = QSlider(Qt.Orientation.Horizontal)
        total_frames = self.controller.get_total_frames()
        self.start_slider.setRange(0, max(total_frames - 1, 1))
        self.start_slider.setValue(self.start_frame)
        self.start_slider.sliderMoved.connect(self._on_start_slider_moved)
        slider_layout.addWidget(self.start_slider)
        
        slider_layout.addWidget(QLabel("End:"))
        self.end_slider = QSlider(Qt.Orientation.Horizontal)
        self.end_slider.setRange(0, max(total_frames - 1, 1))
        self.end_slider.setValue(self.end_frame)
        self.end_slider.sliderMoved.connect(self._on_end_slider_moved)
        slider_layout.addWidget(self.end_slider)
        
        layout.addLayout(slider_layout)
        
        self.setLayout(layout)

    def update_video_frame(self):
        """Обновить видео кадр."""
        frame = self.controller.processor.get_frame_at(self.start_frame)
        if frame is not None:
            # Конвертировать BGR в RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            pixmap = pixmap.scaledToWidth(600, Qt.TransformationMode.SmoothTransformation)
            self.video_label.setPixmap(pixmap)
        
        self.update_timeline()

    def update_timeline(self):
        """Обновить таймлайн."""
        fps = self.controller.get_fps()
        if fps == 0:
            return
        
        # Рисование таймлайна
        timeline_width = 1000
        timeline_height = 80
        timeline_img = np.ones((timeline_height, timeline_width, 3), dtype=np.uint8) * 26
        
        total_frames = self.controller.get_total_frames()
        pixels_per_frame = timeline_width / max(total_frames, 1)
        
        # Отрезок (жёлтый)
        start_x = int(self.start_frame * pixels_per_frame)
        end_x = int(self.end_frame * pixels_per_frame)
        cv2.rectangle(timeline_img, (start_x, 10), (end_x, 70), (0, 200, 255), -1)
        
        # Шкала времени
        cv2.putText(timeline_img, f"0:00", (5, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        total_sec = int(total_frames / fps)
        cv2.putText(timeline_img, f"{total_sec:02d}:{0:02d}", (timeline_width - 80, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Конвертировать в QPixmap
        timeline_rgb = cv2.cvtColor(timeline_img, cv2.COLOR_BGR2RGB)
        h, w, ch = timeline_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(timeline_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.timeline_label.setPixmap(pixmap)

    def _format_time(self, frame_idx: int) -> str:
        """Конвертировать фрейм в MM:SS.FF."""
        fps = self.controller.get_fps()
        if fps == 0:
            return "00:00.00"
        
        total_sec = frame_idx / fps
        minutes = int(total_sec) // 60
        seconds = int(total_sec) % 60
        frames = frame_idx % int(fps)
        
        return f"{minutes:02d}:{seconds:02d}.{frames:02d}"

    def _parse_time(self, time_str: str) -> int:
        """Конвертировать MM:SS.FF в фрейм."""
        fps = self.controller.get_fps()
        if fps == 0:
            return 0
        
        parts = time_str.replace(":", ".").split(".")
        if len(parts) < 3:
            return 0
        
        try:
            minutes = int(parts[0])
            seconds = int(parts[1])
            frames = int(parts[2])
            
            total_sec = minutes * 60 + seconds + frames / fps
            return int(total_sec * fps)
        except:
            return 0

    def _on_start_time_changed(self):
        """Изменение времени начала."""
        new_frame = self._parse_time(self.start_time_edit.text())
        if 0 <= new_frame < self.end_frame:
            self.start_frame = new_frame
            self.start_slider.setValue(self.start_frame)
            self.update_video_frame()

    def _on_end_time_changed(self):
        """Изменение времени конца."""
        new_frame = self._parse_time(self.end_time_edit.text())
        if self.start_frame < new_frame <= self.controller.get_total_frames():
            self.end_frame = new_frame
            self.end_slider.setValue(self.end_frame)
            self.update_timeline()

    def _on_start_slider_moved(self):
        """Движение слайдера начала."""
        new_frame = self.start_slider.value()
        if new_frame < self.end_frame:
            self.start_frame = new_frame
            self.start_time_edit.setText(self._format_time(self.start_frame))
            self.update_video_frame()

    def _on_end_slider_moved(self):
        """Движение слайдера конца."""
        new_frame = self.end_slider.value()
        if self.start_frame < new_frame:
            self.end_frame = new_frame
            self.end_time_edit.setText(self._format_time(self.end_frame))
            self.update_timeline()

    def apply_changes(self):
        """Применить изменения."""
        self.marker.start_frame = self.start_frame
        self.marker.end_frame = self.end_frame
        self.controller.markers_changed.emit()
        self.accept()

    def delete_marker(self):
        """Удалить отрезок."""
        self.controller.delete_marker(self.marker_idx)
        self.reject()
