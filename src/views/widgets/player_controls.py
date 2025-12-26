"""
Player Controls Widget - Professional video player control panel.

Provides playback controls with speed step buttons, play/pause, speed selection,
and additional features for professional video editing.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QComboBox
)
from PySide6.QtCore import Qt, Signal


class PlayerControls(QWidget):
    """Professional video player control panel widget."""

    # Signals
    playClicked = Signal()
    speedStepChanged = Signal(int)  # -1 decrease speed, +1 increase speed
    skipSeconds = Signal(int)  # seconds: +5 or -5 (for hotkeys)
    speedChanged = Signal(float)
    fullscreenClicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(50)  # Fixed height for consistency
        self._is_playing = False  # Track playing state
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create the professional user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)  # Reduced margins for dense layout
        layout.setSpacing(2)  # Reduced spacing between buttons

        # Decrease speed button
        self.speed_down_btn = QPushButton("⏪")
        self.speed_down_btn.setProperty("class", "speed-control")
        self.speed_down_btn.setToolTip("Decrease speed")
        self.speed_down_btn.clicked.connect(lambda: self.speedStepChanged.emit(-1))
        layout.addWidget(self.speed_down_btn)

        # Play/Pause button (large, prominent)
        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setProperty("class", "play-pause")
        self.play_pause_btn.setFixedWidth(60)
        self.play_pause_btn.setToolTip("Play/Pause (Space)")
        self.play_pause_btn.clicked.connect(self.playClicked.emit)
        layout.addWidget(self.play_pause_btn)

        # Increase speed button
        self.speed_up_btn = QPushButton("⏩")
        self.speed_up_btn.setProperty("class", "speed-control")
        self.speed_up_btn.setToolTip("Increase speed")
        self.speed_up_btn.clicked.connect(lambda: self.speedStepChanged.emit(1))
        layout.addWidget(self.speed_up_btn)

        # Stretch to push controls to the right
        layout.addStretch()

        # Speed label
        speed_label = QLabel("Speed:")
        layout.addWidget(speed_label)

        # Speed combo box with extended options
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x", "3.0x", "4.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setFixedWidth(60)
        self.speed_combo.setToolTip("Playback speed")
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)
        layout.addWidget(self.speed_combo)

    def _on_rewind_clicked(self) -> None:
        """Handle rewind button click."""
        # Emit seek to beginning (frame 0)
        self.seek_frame.emit(0)

    def _on_play_pause_clicked(self) -> None:
        """Handle play/pause button click."""
        self._is_playing = not self._is_playing
        self._update_play_pause_button()
        self.play_toggled.emit(self._is_playing)

    def _on_forward_clicked(self) -> None:
        """Handle forward button click."""
        # Emit seek to end (use a large number)
        self.seek_frame.emit(999999)

    def _on_speed_changed(self) -> None:
        """Handle speed combo box change."""
        speed_text = self.speed_combo.currentText()
        speed = float(speed_text.replace('x', ''))
        self.speedChanged.emit(speed)

    def _update_play_pause_button(self) -> None:
        """Update play/pause button text based on current state."""
        if self._is_playing:
            self.play_pause_btn.setText("⏸")
        else:
            self.play_pause_btn.setText("▶")

    def set_playing_state(self, is_playing: bool) -> None:
        """Set the playing state and update button text."""
        self._is_playing = is_playing
        self._update_play_pause_button()

    def get_current_speed(self) -> float:
        """Get the current playback speed."""
        speed_text = self.speed_combo.currentText()
        return float(speed_text.replace('x', ''))

    def set_speed(self, speed: float) -> None:
        """Set the playback speed in the combo box."""
        speed_text = f"{speed:.2f}x"
        if speed_text in [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]:
            self.speed_combo.setCurrentText(speed_text)
        else:
            # Find closest match
            items = [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]
            closest_item = min(items, key=lambda x: abs(float(x.replace('x', '')) - speed))
            self.speed_combo.setCurrentText(closest_item)

    def set_duration(self, total_frames: int) -> None:
        """Set the total duration (for compatibility with existing code)."""
        # This method is kept for compatibility but doesn't do anything
        # since our player controls don't display duration
        pass

    def set_current_frame(self, frame: int) -> None:
        """Set the current frame (for compatibility with existing code)."""
        # This method is kept for compatibility but doesn't do anything
        # since our player controls don't display current frame
        pass

    def update_play_pause_button(self, is_playing: bool) -> None:
        """Update play/pause button text (for compatibility with existing code)."""
        self._is_playing = is_playing
        self._update_play_pause_button()

    def update_time_label(self, current_sec: float, total_sec: float) -> None:
        """Update time display (for compatibility with existing code)."""
        # This method is kept for compatibility but doesn't do anything
        # since our player controls don't display time labels
        pass
