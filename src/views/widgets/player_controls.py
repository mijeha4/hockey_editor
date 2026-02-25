"""
Player Controls Widget — панель управления воспроизведением видео.
Включает кнопки, скорость и временну́ю метку.
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
        self.setFixedHeight(40)
        self._is_playing = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 4)
        layout.setSpacing(4)

        # Замедлить
        self.speed_down_btn = QPushButton("⏪")
        self.speed_down_btn.setProperty("class", "speed-control")
        self.speed_down_btn.setToolTip("Замедлить")
        self.speed_down_btn.setFixedSize(36, 28)
        self.speed_down_btn.clicked.connect(lambda: self.speedStepChanged.emit(-1))
        layout.addWidget(self.speed_down_btn)

        # Воспроизведение / Пауза
        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setProperty("class", "play-pause")
        self.play_pause_btn.setFixedSize(44, 28)
        self.play_pause_btn.setToolTip("Воспроизведение / Пауза (Пробел)")
        self.play_pause_btn.clicked.connect(self.playClicked.emit)
        layout.addWidget(self.play_pause_btn)

        # Ускорить
        self.speed_up_btn = QPushButton("⏩")
        self.speed_up_btn.setProperty("class", "speed-control")
        self.speed_up_btn.setToolTip("Ускорить")
        self.speed_up_btn.setFixedSize(36, 28)
        self.speed_up_btn.clicked.connect(lambda: self.speedStepChanged.emit(1))
        layout.addWidget(self.speed_up_btn)

        layout.addSpacing(8)

        # ── Временна́я метка ──
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet(
            "color: #aaaaaa; font-family: Consolas, monospace; font-size: 12px;"
        )
        self.time_label.setMinimumWidth(110)
        layout.addWidget(self.time_label)

        layout.addStretch()

        # Скорость
        speed_label = QLabel("Скорость:")
        speed_label.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(speed_label)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems([
            "0.25x", "0.5x", "0.75x", "1.0x",
            "1.25x", "1.5x", "2.0x", "3.0x", "4.0x"
        ])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setFixedWidth(65)
        self.speed_combo.setToolTip("Скорость воспроизведения")
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        layout.addWidget(self.speed_combo)

    def _on_speed_changed(self) -> None:
        speed_text = self.speed_combo.currentText()
        speed = float(speed_text.replace('x', ''))
        self.speedChanged.emit(speed)

    def _update_play_pause_button(self) -> None:
        self.play_pause_btn.setText("⏸" if self._is_playing else "▶")

    # ── Public API ──

    def set_playing_state(self, is_playing: bool) -> None:
        self._is_playing = is_playing
        self._update_play_pause_button()

    def update_play_pause_button(self, is_playing: bool) -> None:
        self._is_playing = is_playing
        self._update_play_pause_button()

    def get_current_speed(self) -> float:
        speed_text = self.speed_combo.currentText()
        return float(speed_text.replace('x', ''))

    def set_speed(self, speed: float) -> None:
        speed_text = f"{speed:.2f}x"
        items = [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]
        if speed_text in items:
            self.speed_combo.setCurrentText(speed_text)
        else:
            closest = min(items, key=lambda x: abs(float(x.replace('x', '')) - speed))
            self.speed_combo.setCurrentText(closest)

    def update_time_label(self, current_sec: float, total_sec: float) -> None:
        """Обновить отображение времени."""
        self.time_label.setText(
            f"{self._fmt(current_sec)} / {self._fmt(total_sec)}"
        )

    def set_duration(self, total_frames: int) -> None:
        pass

    def set_current_frame(self, frame: int) -> None:
        pass

    @staticmethod
    def _fmt(seconds: float) -> str:
        s = max(0, int(seconds))
        if s >= 3600:
            return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
        return f"{s // 60}:{s % 60:02d}"