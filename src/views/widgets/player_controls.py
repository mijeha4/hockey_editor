"""
Player Controls Widget - панель управления воспроизведением видео.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QComboBox
)
from PySide6.QtCore import Qt, Signal


class PlayerControls(QWidget):
    """Панель управления воспроизведением видео."""

    playClicked = Signal()
    speedStepChanged = Signal(int)
    skipSeconds = Signal(int)
    speedChanged = Signal(float)
    fullscreenClicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(50)
        self._is_playing = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(2)

        self.speed_down_btn = QPushButton("⏪")
        self.speed_down_btn.setProperty("class", "speed-control")
        self.speed_down_btn.setToolTip("Замедлить")
        self.speed_down_btn.clicked.connect(lambda: self.speedStepChanged.emit(-1))
        layout.addWidget(self.speed_down_btn)

        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setProperty("class", "play-pause")
        self.play_pause_btn.setFixedWidth(60)
        self.play_pause_btn.setToolTip("Воспроизведение / Пауза (Пробел)")
        self.play_pause_btn.clicked.connect(self.playClicked.emit)
        layout.addWidget(self.play_pause_btn)

        self.speed_up_btn = QPushButton("⏩")
        self.speed_up_btn.setProperty("class", "speed-control")
        self.speed_up_btn.setToolTip("Ускорить")
        self.speed_up_btn.clicked.connect(lambda: self.speedStepChanged.emit(1))
        layout.addWidget(self.speed_up_btn)

        layout.addStretch()

        speed_label = QLabel("Скорость:")
        layout.addWidget(speed_label)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x", "3.0x", "4.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setFixedWidth(60)
        self.speed_combo.setToolTip("Скорость воспроизведения")
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        layout.addWidget(self.speed_combo)

    def _on_rewind_clicked(self) -> None:
        self.seek_frame.emit(0)

    def _on_play_pause_clicked(self) -> None:
        self._is_playing = not self._is_playing
        self._update_play_pause_button()
        self.play_toggled.emit(self._is_playing)

    def _on_forward_clicked(self) -> None:
        self.seek_frame.emit(999999)

    def _on_speed_changed(self) -> None:
        speed_text = self.speed_combo.currentText()
        speed = float(speed_text.replace('x', ''))
        self.speedChanged.emit(speed)

    def _update_play_pause_button(self) -> None:
        if self._is_playing:
            self.play_pause_btn.setText("⏸")
        else:
            self.play_pause_btn.setText("▶")

    def set_playing_state(self, is_playing: bool) -> None:
        self._is_playing = is_playing
        self._update_play_pause_button()

    def get_current_speed(self) -> float:
        speed_text = self.speed_combo.currentText()
        return float(speed_text.replace('x', ''))

    def set_speed(self, speed: float) -> None:
        speed_text = f"{speed:.2f}x"
        if speed_text in [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]:
            self.speed_combo.setCurrentText(speed_text)
        else:
            items = [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]
            closest_item = min(items, key=lambda x: abs(float(x.replace('x', '')) - speed))
            self.speed_combo.setCurrentText(closest_item)

    def set_duration(self, total_frames: int) -> None:
        pass

    def set_current_frame(self, frame: int) -> None:
        pass

    def update_play_pause_button(self, is_playing: bool) -> None:
        self._is_playing = is_playing
        self._update_play_pause_button()

    def update_time_label(self, current_sec: float, total_sec: float) -> None:
        pass