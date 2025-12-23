from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QSlider
)


class PlayerControls(QWidget):
    """Панель управления воспроизведением видео."""

    # Сигналы
    play_clicked = Signal()
    pause_clicked = Signal()
    seek_requested = Signal(int)  # frame_index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self._setup_ui()

    def _setup_ui(self):
        """Создать интерфейс."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(2)

        # Кнопки управления
        self.play_btn = QPushButton("▶")
        self.play_btn.clicked.connect(self._on_play_clicked)
        layout.addWidget(self.play_btn)

        self.pause_btn = QPushButton("⏸")
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        layout.addWidget(self.pause_btn)

        # Слайдер для навигации
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)  # Начальный диапазон
        self.slider.sliderMoved.connect(self._on_slider_moved)
        layout.addWidget(self.slider)

        # Метка времени
        self.time_label = QLabel("00:00 / 00:00")
        layout.addWidget(self.time_label)

        layout.addStretch()

    def _on_play_clicked(self):
        """Обработка нажатия Play."""
        self.play_clicked.emit()

    def _on_pause_clicked(self):
        """Обработка нажатия Pause."""
        self.pause_clicked.emit()

    def _on_slider_moved(self, value: int):
        """Обработка движения слайдера."""
        self.seek_requested.emit(value)

    def set_duration(self, total_frames: int):
        """Установить общую длительность видео."""
        self.slider.setRange(0, total_frames)

    def set_current_frame(self, frame: int):
        """Установить текущий кадр."""
        self.slider.blockSignals(True)
        self.slider.setValue(frame)
        self.slider.blockSignals(False)

    def set_time_display(self, current_sec: float, total_sec: float):
        """Установить отображение времени."""
        def fmt(s):
            m = int(s) // 60
            sec = int(s) % 60
            return f"{m:02d}:{sec:02d}"

        self.time_label.setText(f"{fmt(current_sec)} / {fmt(total_sec)}")

    def set_playing_state(self, is_playing: bool):
        """Установить состояние воспроизведения."""
        # Можно изменить стиль кнопок в зависимости от состояния
        pass
