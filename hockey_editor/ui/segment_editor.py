# ui/segment_editor.py
# Полностью исправленная версия — работает с новой моделью Marker (event_name)

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QSpinBox, QPushButton, QComboBox, QDialogButtonBox
)
from PySide6.QtCore import Qt
from ..utils.custom_events import get_custom_event_manager


class SegmentEditorDialog(QDialog):
    """Диалог редактирования отрезка"""

    def __init__(self, controller, marker_idx, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.marker_idx = marker_idx
        self.marker = controller.markers[marker_idx]
        self.event_manager = get_custom_event_manager()

        self.setWindowTitle(f"Edit Segment - {self.marker.event_name}")
        self.setModal(True)
        self.resize(400, 250)

        layout = QVBoxLayout(self)

        # === Имя события ===
        event_layout = QHBoxLayout()
        event_layout.addWidget(QLabel("Event:"))
        self.event_combo = QComboBox()
        for event in self.event_manager.get_all_events():
            self.event_combo.addItem(event.name, event.name)
        self.event_combo.setCurrentText(self.marker.event_name)
        event_layout.addWidget(self.event_combo)
        layout.addLayout(event_layout)

        # === Начало ===
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start frame:"))
        self.start_spin = QSpinBox()
        self.start_spin.setRange(0, controller.get_total_frames() - 1)
        self.start_spin.setValue(self.marker.start_frame)
        start_layout.addWidget(self.start_spin)
        layout.addLayout(start_layout)

        # === Конец ===
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("End frame:"))
        self.end_spin = QSpinBox()
        self.end_spin.setRange(0, controller.get_total_frames() - 1)
        self.end_spin.setValue(self.marker.end_frame)
        self.end_spin.setMinimum(self.marker.start_frame + 1)
        end_layout.addWidget(self.end_spin)
        layout.addLayout(end_layout)

        # === Заметка ===
        note_layout = QHBoxLayout()
        note_layout.addWidget(QLabel("Note:"))
        self.note_edit = QLineEdit(self.marker.note)
        note_layout.addWidget(self.note_edit)
        layout.addLayout(note_layout)

        # === Кнопки ===
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Синхронизация спинбоксов
        self.start_spin.valueChanged.connect(self._on_start_changed)
        self.end_spin.valueChanged.connect(self._on_end_changed)

    def _on_start_changed(self, value):
        if value >= self.marker.end_frame:
            self.end_spin.setValue(value + 1)
        self.end_spin.setMinimum(value + 1)

    def _on_end_changed(self, value):
        if value <= self.marker.start_frame:
            self.start_spin.setValue(value - 1)
        self.start_spin.setMaximum(value - 1)

    def accept(self):
        """Сохранить изменения"""
        old_marker = self.marker

        new_marker = type(old_marker)(
            start_frame=self.start_spin.value(),
            end_frame=self.end_spin.value(),
            event_name=self.event_combo.currentText(),
            note=self.note_edit.text().strip()
        )

        # Применяем через команду для undo/redo
        from ..utils.undo_redo import ModifyMarkerCommand
        command = ModifyMarkerCommand(
            self.controller.markers,
            self.marker_idx,
            old_marker,
            new_marker
        )
        from ..utils.undo_redo import UndoRedoManager
        self.controller.undo_redo.push_command(command)

        # Обновляем UI
        self.controller.markers_changed.emit()
        self.controller.timeline_update.emit()

        super().accept()