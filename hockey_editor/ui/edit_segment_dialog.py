"""
Диалог редактирования отрезка (PySide6).
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ..models.marker import Marker
from ..utils.custom_events import get_custom_event_manager
from ..utils.time_utils import format_time, frames_to_time, time_to_frames, validate_time_format
from ..utils.localization_manager import get_localization_manager


class EditSegmentDialog(QDialog):
    """Диалог для редактирования отрезка (маркера)."""

    def __init__(self, marker: Marker, fps: float, parent=None):
        super().__init__(parent)
        self.marker = marker
        self.fps = fps or 30.0
        self.localization = get_localization_manager()

        # ИСПРАВЛЕНО: использовать event_name вместо type.name
        title = self.localization.tr("dialog_title_edit_segment").format(event_name=marker.event_name)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(500, 300)
        self.setStyleSheet(self._get_dark_stylesheet())

        self._setup_ui()

        # Подключить сигнал изменения языка
        self.localization.language_changed.connect(self.retranslate_ui)

    def _setup_ui(self):
        """Создать интерфейс."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Тип события
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel(self.localization.tr("lbl_event_type")))
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
        start_layout.addWidget(QLabel(self.localization.tr("lbl_start_time")))
        self.start_time_edit = QLineEdit()
        self.start_time_edit.setText(frames_to_time(self.marker.start_frame, self.fps))
        self.start_time_edit.textChanged.connect(self._update_start_frame_display)
        self.start_time_edit.editingFinished.connect(self._validate_start_time)
        start_layout.addWidget(self.start_time_edit)

        self.start_frame_display = QLabel(f"({self.marker.start_frame} frames)")
        self.start_frame_display.setMinimumWidth(100)
        start_layout.addWidget(self.start_frame_display)
        start_layout.addStretch()
        layout.addLayout(start_layout)

        # Конец отрезка
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel(self.localization.tr("lbl_end_time")))
        self.end_time_edit = QLineEdit()
        self.end_time_edit.setText(frames_to_time(self.marker.end_frame, self.fps))
        self.end_time_edit.textChanged.connect(self._update_end_frame_display)
        self.end_time_edit.editingFinished.connect(self._validate_end_time)
        end_layout.addWidget(self.end_time_edit)

        self.end_frame_display = QLabel(f"({self.marker.end_frame} frames)")
        self.end_frame_display.setMinimumWidth(100)
        end_layout.addWidget(self.end_frame_display)
        end_layout.addStretch()
        layout.addLayout(end_layout)

        # Продолжительность
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel(self.localization.tr("lbl_duration")))
        self.duration_label = QLabel(self._format_duration())
        self.duration_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.duration_label.setStyleSheet("color: #ffcc00;")
        duration_layout.addWidget(self.duration_label)
        duration_layout.addStretch()
        layout.addLayout(duration_layout)

        # Примечание
        note_layout = QHBoxLayout()
        note_layout.addWidget(QLabel(self.localization.tr("lbl_note")))
        self.note_edit = QLineEdit()
        self.note_edit.setText(self.marker.note or "")
        note_layout.addWidget(self.note_edit)
        layout.addLayout(note_layout)

        layout.addStretch()

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_btn = QPushButton(f"✓ {self.localization.tr('btn_save')}")
        ok_btn.setMaximumWidth(100)
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton(f"✕ {self.localization.tr('btn_cancel')}")
        cancel_btn.setMaximumWidth(100)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _format_duration(self) -> str:
        """Получить продолжительность отрезка."""
        start_frames = time_to_frames(self.start_time_edit.text(), self.fps)
        end_frames = time_to_frames(self.end_time_edit.text(), self.fps)
        duration_frames = max(0, end_frames - start_frames)

        if self.fps <= 0:
            return "00:00"

        duration_secs = duration_frames / self.fps
        minutes = int(duration_secs) // 60
        seconds = int(duration_secs) % 60
        return f"{minutes:02d}:{seconds:02d} ({duration_frames} frames)"

    def _update_start_frame_display(self):
        """Обновить отображение начального кадра."""
        frames = time_to_frames(self.start_time_edit.text(), self.fps)
        self.start_frame_display.setText(f"({frames} frames)")
        self.duration_label.setText(self._format_duration())

    def _update_end_frame_display(self):
        """Обновить отображение конечного кадра."""
        frames = time_to_frames(self.end_time_edit.text(), self.fps)
        self.end_frame_display.setText(f"({frames} frames)")
        self.duration_label.setText(self._format_duration())

    def _validate_start_time(self):
        """Валидация времени начала."""
        time_str = self.start_time_edit.text()
        if not validate_time_format(time_str):
            # Reset to previous valid value
            self.start_time_edit.setText(frames_to_time(self.marker.start_frame, self.fps))
        self._update_start_frame_display()

    def _validate_end_time(self):
        """Валидация времени конца."""
        time_str = self.end_time_edit.text()
        if not validate_time_format(time_str):
            # Reset to previous valid value
            self.end_time_edit.setText(frames_to_time(self.marker.end_frame, self.fps))
        self._update_end_frame_display()

    def get_marker(self) -> Marker:
        """Получить отредактированный маркер."""
        # Конвертировать время в кадры
        start_frames = time_to_frames(self.start_time_edit.text(), self.fps)
        end_frames = time_to_frames(self.end_time_edit.text(), self.fps)

        return Marker(
            start_frame=start_frames,
            end_frame=end_frames,
            event_name=self.type_combo.currentData(),
            note=self.note_edit.text()
        )

    def retranslate_ui(self):
        """Перевести интерфейс на новый язык."""
        # Заголовок окна
        title = self.localization.tr("dialog_title_edit_segment").format(event_name=self.marker.event_name)
        self.setWindowTitle(title)

        # Найти и обновить все метки
        for label in self.findChildren(QLabel):
            if label.text() == "Event Type:" or self.localization.tr("lbl_event_type", "Event Type:") in label.text():
                label.setText(self.localization.tr("lbl_event_type"))
            elif label.text() == "Start Time:" or self.localization.tr("lbl_start_time", "Start Time:") in label.text():
                label.setText(self.localization.tr("lbl_start_time"))
            elif label.text() == "End Time:" or self.localization.tr("lbl_end_time", "End Time:") in label.text():
                label.setText(self.localization.tr("lbl_end_time"))
            elif label.text() == "Duration:" or self.localization.tr("lbl_duration", "Duration:") in label.text():
                label.setText(self.localization.tr("lbl_duration"))
            elif label.text() == "Note:" or self.localization.tr("lbl_note", "Note:") in label.text():
                label.setText(self.localization.tr("lbl_note"))

        # Обновить кнопки
        for btn in self.findChildren(QPushButton):
            if "✓ Save" in btn.text() or btn.text() == f"✓ {self.localization.tr('btn_save', 'Save')}":
                btn.setText(f"✓ {self.localization.tr('btn_save')}")
            elif "✕ Cancel" in btn.text() or btn.text() == f"✕ {self.localization.tr('btn_cancel', 'Cancel')}":
                btn.setText(f"✕ {self.localization.tr('btn_cancel')}")

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
