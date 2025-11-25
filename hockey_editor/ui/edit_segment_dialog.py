"""
Диалог редактирования отрезка (PySide6).
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton,
    QComboBox, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ..models.marker import Marker
from ..utils.custom_events import get_custom_event_manager
from ..utils.time_utils import format_time


class EditSegmentDialog(QDialog):
    """Диалог для редактирования отрезка (маркера)."""

    def __init__(self, marker: Marker, fps: float, parent=None):
        super().__init__(parent)
        self.marker = marker
        self.fps = fps or 30.0
        # ИСПРАВЛЕНО: использовать event_name вместо type.name
        self.setWindowTitle(f"Edit Segment - {marker.event_name}")
        self.setModal(True)
        self.resize(500, 300)
        self.setStyleSheet(self._get_dark_stylesheet())

        self._setup_ui()

    def _setup_ui(self):
        """Создать интерфейс."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Тип события
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Event Type:"))
        self.type_combo = QComboBox()
        # ИСПРАВЛЕНО: использовать CustomEventManager вместо EventType enum
        self.event_manager = get_custom_event_manager()
        events = self.event_manager.get_all_events()
        for event in events:
            self.type_combo.addItem(event.name, event.name)
        # Найти текущий event_name
        current_index = 0
        for i, event in enumerate(events):
            if event.name == self.marker.event_name:
                current_index = i
                break
        self.type_combo.setCurrentIndex(current_index)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # Начало отрезка
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start Frame:"))
        self.start_frame_box = QSpinBox()
        self.start_frame_box.setMinimum(0)
        self.start_frame_box.setMaximum(1000000)
        self.start_frame_box.setValue(self.marker.start_frame)
        self.start_frame_box.valueChanged.connect(self._update_start_time_display)
        start_layout.addWidget(self.start_frame_box)
        
        self.start_time_display = QLabel(self._format_frame_time(self.marker.start_frame))
        self.start_time_display.setMinimumWidth(80)
        start_layout.addWidget(self.start_time_display)
        start_layout.addStretch()
        layout.addLayout(start_layout)
        
        # Конец отрезка
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("End Frame:"))
        self.end_frame_box = QSpinBox()
        self.end_frame_box.setMinimum(0)
        self.end_frame_box.setMaximum(1000000)
        self.end_frame_box.setValue(self.marker.end_frame)
        self.end_frame_box.valueChanged.connect(self._update_end_time_display)
        end_layout.addWidget(self.end_frame_box)
        
        self.end_time_display = QLabel(self._format_frame_time(self.marker.end_frame))
        self.end_time_display.setMinimumWidth(80)
        end_layout.addWidget(self.end_time_display)
        end_layout.addStretch()
        layout.addLayout(end_layout)
        
        # Продолжительность
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration:"))
        self.duration_label = QLabel(self._format_duration())
        self.duration_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.duration_label.setStyleSheet("color: #ffcc00;")
        duration_layout.addWidget(self.duration_label)
        duration_layout.addStretch()
        layout.addLayout(duration_layout)
        
        # Примечание
        note_layout = QHBoxLayout()
        note_layout.addWidget(QLabel("Note:"))
        self.note_edit = QLineEdit()
        self.note_edit.setText(self.marker.note or "")
        note_layout.addWidget(self.note_edit)
        layout.addLayout(note_layout)
        
        layout.addStretch()
        
        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("✓ Save")
        ok_btn.setMaximumWidth(100)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("✕ Cancel")
        cancel_btn.setMaximumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)

    def _format_frame_time(self, frame_idx: int) -> str:
        """Форматировать время кадра в MM:SS.FF."""
        if self.fps <= 0:
            return "00:00.00"
        
        total_secs = frame_idx / self.fps
        minutes = int(total_secs) // 60
        seconds = int(total_secs) % 60
        frames = frame_idx % int(self.fps)
        return f"{minutes:02d}:{seconds:02d}.{frames:02d}"

    def _format_duration(self) -> str:
        """Получить продолжительность отрезка."""
        duration_frames = self.end_frame_box.value() - self.start_frame_box.value()
        if self.fps <= 0:
            return "00:00"
        
        duration_secs = duration_frames / self.fps
        minutes = int(duration_secs) // 60
        seconds = int(duration_secs) % 60
        return f"{minutes:02d}:{seconds:02d} ({duration_frames} frames)"

    def _update_start_time_display(self):
        """Обновить отображение начального времени."""
        frame = self.start_frame_box.value()
        self.start_time_display.setText(self._format_frame_time(frame))
        self.duration_label.setText(self._format_duration())

    def _update_end_time_display(self):
        """Обновить отображение конечного времени."""
        frame = self.end_frame_box.value()
        self.end_time_display.setText(self._format_frame_time(frame))
        self.duration_label.setText(self._format_duration())

    def get_marker(self) -> Marker:
        """Получить отредактированный маркер."""
        # ИСПРАВЛЕНО: использовать event_name вместо type
        return Marker(
            start_frame=self.start_frame_box.value(),
            end_frame=self.end_frame_box.value(),
            event_name=self.type_combo.currentData(),
            note=self.note_edit.text()
        )

    def _get_dark_stylesheet(self) -> str:
        """Тёмный стиль для диалога."""
        return """
        QDialog {
            background-color: #1a1a1a;
            color: #ffffff;
        }
        QLabel {
            color: #ffffff;
        }
        QSpinBox, QLineEdit, QComboBox {
            background-color: #333333;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 4px;
            border-radius: 3px;
        }
        QPushButton {
            background-color: #333333;
            color: white;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #444444;
        }
        """
