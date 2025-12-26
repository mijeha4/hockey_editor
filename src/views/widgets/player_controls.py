"""
Player Controls Widget - Video player control panel.

Provides playback controls with rewind, play/pause, forward buttons,
and speed selection combo box.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QLabel, QComboBox
)
from PySide6.QtCore import Qt, Signal


class PlayerControls(QWidget):
    """Video player control panel widget."""

    # Signals
    play_toggled: Signal = Signal(bool)  # True for play, False for pause
    speed_changed: Signal = Signal(float)  # Speed multiplier (e.g., 1.0, 1.5)
    seek_frame: Signal = Signal(int)  # Frame number to seek to

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._is_playing: bool = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Rewind button
        self.rewind_btn = QPushButton("<<")
        self.rewind_btn.setFixedWidth(40)
        self.rewind_btn.setToolTip("Rewind")
        self.rewind_btn.clicked.connect(self._on_rewind_clicked)
        layout.addWidget(self.rewind_btn)

        # Play/Pause button (larger)
        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setFixedWidth(60)
        self.play_pause_btn.setToolTip("Play/Pause")
        self.play_pause_btn.clicked.connect(self._on_play_pause_clicked)
        layout.addWidget(self.play_pause_btn)

        # Forward button
        self.forward_btn = QPushButton(">>")
        self.forward_btn.setFixedWidth(40)
        self.forward_btn.setToolTip("Forward")
        self.forward_btn.clicked.connect(self._on_forward_clicked)
        layout.addWidget(self.forward_btn)

        # Stretch to push controls to the right
        layout.addStretch()

        # Speed label
        speed_label = QLabel("Speed:")
        layout.addWidget(speed_label)

        # Speed combo box
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1.0x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.setFixedWidth(70)
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
        self.speed_changed.emit(speed)

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
