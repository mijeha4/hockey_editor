# ui/video_window.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSlider, QHBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap, QKeySequence, QShortcut
import cv2


class VideoWindow(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.controller = main_window.controller
        self.setWindowTitle("Полноэкранный просмотр")
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.resize(1200, 700)

        self.current_frame = 0
        self.playing = False

        self.setup_ui()
        self.setup_shortcuts()
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_frame)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Видео
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setMinimumSize(640, 360)
        layout.addWidget(self.video_label)

        # Управление
        controls = QHBoxLayout()
        controls.addStretch()

        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.toggle_playback)
        controls.addWidget(self.play_btn)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.sliderMoved.connect(self.seek_from_slider)
        controls.addWidget(self.slider, stretch=1)

        controls.addStretch()
        layout.addLayout(controls)

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.close)
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_layout.addWidget(close_btn)
        close_layout.addStretch()
        layout.addLayout(close_layout)

        self.update_frame()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Space"), self, self.toggle_playback)
        QShortcut(QKeySequence("Esc"), self, self.close)
        QShortcut(QKeySequence("Left"), self, lambda: self.seek_relative(-30))
        QShortcut(QKeySequence("Right"), self, lambda: self.seek_relative(30))

    def toggle_playback(self):
        self.playing = not self.playing
        self.play_btn.setText("Pause" if self.playing else "Play")
        if self.playing:
            self.timer.start(33)  # ~30 fps
        else:
            self.timer.stop()

    def next_frame(self):
        if not self.controller.processor.cap:
            return
        ret, frame = self.controller.processor.cap.read()
        if not ret:
            self.playing = False
            self.play_btn.setText("Play")
            self.timer.stop()
            return
        self.current_frame = int(self.controller.processor.cap.get(cv2.CAP_PROP_POS_FRAMES))
        self.display_frame(frame)
        self.update_slider()

    def display_frame(self, frame_bgr):
        if frame_bgr is None:
            return
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        scaled = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled)

    def update_frame(self):
        frame = self.controller.processor.get_frame(self.current_frame)
        if frame is not None:
            self.display_frame(frame)

    def update_slider(self):
        if self.controller.processor.total_frames > 0:
            pos = self.current_frame / self.controller.processor.total_frames
            self.slider.blockSignals(True)
            self.slider.setValue(int(pos * 1000))
            self.slider.blockSignals(False)

    def seek_from_slider(self, value):
        if self.controller.processor.total_frames > 0:
            frame = int(value / 1000 * self.controller.processor.total_frames)
            self.seek_to_frame(frame)

    def seek_to_frame(self, frame):
        self.current_frame = max(0, min(frame, self.controller.processor.total_frames - 1))
        self.controller.processor.seek(self.current_frame)
        self.update_frame()
        self.update_slider()

    def seek_relative(self, frames):
        self.seek_to_frame(self.current_frame + frames)

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()