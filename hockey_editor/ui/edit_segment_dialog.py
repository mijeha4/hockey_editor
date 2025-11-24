"""
Диалог редактирования отрезка.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QPushButton, QComboBox
from PyQt6.QtCore import Qt
from ..models.marker import Marker, EventType
from ..utils.time_utils import format_time


class EditSegmentDialog(QDialog):
    """Диалог для редактирования отрезка (маркера)."""

    def __init__(self, marker: Marker, fps: float, parent=None):
        super().__init__(parent)
        self.marker = marker
        self.fps = fps or 30.0
        self.setWindowTitle(f"Edit Segment - {marker.type.value}")
        self.setModal(True)
        self.resize(400, 200)
        
        self._setup_ui()

    def _setup_ui(self):
        """Создать интерфейс."""
        layout = QVBoxLayout(self)
        
        # Тип события
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Type:"))
        self.type_combo = QComboBox()
        for et in EventType:
            self.type_combo.addItem(et.value, et)
        self.type_combo.setCurrentIndex(list(EventType).index(self.marker.type))
        type_layout.addWidget(self.type_combo)
        layout.addLayout(type_layout)
        
        # Начало
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start Frame:"))
        self.start_frame_box = QSpinBox()
        self.start_frame_box.setMinimum(0)
        self.start_frame_box.setMaximum(1000000)
        self.start_frame_box.setValue(self.marker.start_frame)
        start_layout.addWidget(self.start_frame_box)
        
        start_time_label = QLabel(format_time(int(self.marker.start_frame / self.fps)))
        self.start_time_display = start_time_label
        start_layout.addWidget(start_time_label)
        
        layout.addLayout(start_layout)
        
        # Конец
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("End Frame:"))
        self.end_frame_box = QSpinBox()
        self.end_frame_box.setMinimum(0)
        self.end_frame_box.setMaximum(1000000)
        self.end_frame_box.setValue(self.marker.end_frame)
        end_layout.addWidget(self.end_frame_box)
        
        end_time_label = QLabel(format_time(int(self.marker.end_frame / self.fps)))
        self.end_time_display = end_time_label
        end_layout.addWidget(end_time_label)
        
        layout.addLayout(end_layout)
        
        # Примечание
        note_layout = QHBoxLayout()
        note_layout.addWidget(QLabel("Note:"))
        # TODO: добавить QLineEdit для примечания
        layout.addLayout(note_layout)
        
        # Кнопки
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        # Сигналы
        self.start_frame_box.valueChanged.connect(self._update_start_time_display)
        self.end_frame_box.valueChanged.connect(self._update_end_time_display)

    def _update_start_time_display(self):
        """Обновить отображение начального времени."""
        frame = self.start_frame_box.value()
        self.start_time_display.setText(format_time(int(frame / self.fps)))

    def _update_end_time_display(self):
        """Обновить отображение конечного времени."""
        frame = self.end_frame_box.value()
        self.end_time_display.setText(format_time(int(frame / self.fps)))

    def get_marker(self) -> Marker:
        """Получить отредактированный маркер."""
        return Marker(
            start_frame=self.start_frame_box.value(),
            end_frame=self.end_frame_box.value(),
            type=EventType[self.type_combo.currentText().upper().replace("Ё", "E")],
            note=self.marker.note
        )
