from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QComboBox, QSlider
)


class PlayerControls(QWidget):
    """Профессиональная панель управления видео плеером."""

    # Сигналы
    playClicked = Signal()
    speedStepChanged = Signal(int)  # -1 уменьшить скорость, +1 увеличить скорость
    skipSeconds = Signal(int)  # seconds: +5 или -5 (для горячих клавиш)
    speedChanged = Signal(float)
    fullscreenClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)  # Фиксированная высота
        self._setup_ui()

    def _setup_ui(self):
        """Создать интерфейс панели управления."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)  # Уменьшенные отступы для более плотной компоновки
        layout.setSpacing(2)  # Уменьшенные промежутки между кнопками

        # Уменьшить скорость
        self.speed_down_btn = QPushButton("⏪")
        self.speed_down_btn.setProperty("class", "speed-control")
        self.speed_down_btn.setToolTip("Уменьшить скорость")
        self.speed_down_btn.clicked.connect(lambda: self.speedStepChanged.emit(-1))
        layout.addWidget(self.speed_down_btn)

        # Play/Pause (большая кнопка)
        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setProperty("class", "play-pause")
        self.play_pause_btn.setFixedWidth(60)
        self.play_pause_btn.setToolTip("Play/Pause (Space)")
        self.play_pause_btn.clicked.connect(self.playClicked.emit)
        layout.addWidget(self.play_pause_btn)

        # Увеличить скорость
        self.speed_up_btn = QPushButton("⏩")
        self.speed_up_btn.setProperty("class", "speed-control")
        self.speed_up_btn.setToolTip("Увеличить скорость")
        self.speed_up_btn.clicked.connect(lambda: self.speedStepChanged.emit(1))
        layout.addWidget(self.speed_up_btn)

        # Растяжка
        layout.addStretch()

        # Speed combo
        speed_label = QLabel("Speed:")
        layout.addWidget(speed_label)

        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x", "3.0x", "4.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setFixedWidth(60)
        self.speed_combo.setToolTip("Скорость воспроизведения")
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        layout.addWidget(self.speed_combo)

    def _on_skip_start(self):
        """Перемотка в начало."""
        self.skipSeconds.emit(-999999)  # Большое отрицательное значение для перехода в начало

    def _on_skip_end(self):
        """Перемотка в конец."""
        self.skipSeconds.emit(999999)  # Большое положительное значение для перехода в конец

    def _on_speed_changed(self):
        """Изменение скорости воспроизведения."""
        speed_text = self.speed_combo.currentText()
        speed = float(speed_text.replace('x', ''))
        self.speedChanged.emit(speed)

    def update_play_pause_button(self, is_playing: bool):
        """Обновить текст кнопки Play/Pause."""
        if is_playing:
            self.play_pause_btn.setText("⏸")
        else:
            self.play_pause_btn.setText("▶")

    def update_time_label(self, current_sec: float, total_sec: float):
        """Обновить отображение времени. (Метка времени удалена из интерфейса)"""
        # Метод оставлен для совместимости с MainWindow, но не делает ничего
        pass

    def set_speed(self, speed: float):
        """Установить скорость в combo box."""
        speed_text = f"{speed:.2f}x"
        if speed_text in [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]:
            self.speed_combo.setCurrentText(speed_text)
        else:
            # Найти ближайшее значение
            items = [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]
            closest_item = min(items, key=lambda x: abs(float(x.replace('x', '')) - speed))
            self.speed_combo.setCurrentText(closest_item)
