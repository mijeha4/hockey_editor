"""
Диалог редактирования отрезка (PySide6).
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QWidget, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from ..models.marker import Marker
from ..utils.custom_events import get_custom_event_manager
from ..utils.time_utils import format_time, frames_to_time, time_to_frames, validate_time_format
from ..core.video_controller import VideoController


class EditSegmentDialog(QDialog):
    """Диалог для редактирования отрезка (маркера)."""

    def __init__(self, marker: Marker, fps: float, video_controller: VideoController, parent=None):
        super().__init__(parent)
        self.marker = marker
        self.fps = fps or 30.0
        self.video_controller = video_controller

        # Использовать event_name для заголовка
        event = get_custom_event_manager().get_event(marker.event_name)
        event_display_name = event.get_localized_name() if event else marker.event_name
        title = f"Редактировать отрезок - {event_display_name}"
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(550, 280)
        self.setStyleSheet(self._get_dark_stylesheet())

        self._setup_ui()

    def _setup_ui(self):
        """Создать интерфейс."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Тип события
        type_layout = QHBoxLayout()
        type_label = QLabel("Тип события:")
        type_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        type_label.setMinimumWidth(80)
        self.type_combo = QComboBox()
        self.event_manager = get_custom_event_manager()
        events = self.event_manager.get_all_events()
        for event in events:
            display_name = event.get_localized_name()
            self.type_combo.addItem(display_name, event.name)
        # Найти текущий event_name
        current_index = 0
        for i, event in enumerate(events):
            if event.name == self.marker.event_name:
                current_index = i
                break
        self.type_combo.setCurrentIndex(current_index)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo, 1)
        layout.addLayout(type_layout)

        # Сетка для времени (Начало, Конец, Длительность)
        time_grid = QGridLayout()
        time_grid.setSpacing(5)
        time_grid.setColumnStretch(0, 0)  # Подписи
        time_grid.setColumnStretch(1, 1)  # Поля ввода
        time_grid.setColumnStretch(2, 0)  # Кнопки [-1] [+1]
        time_grid.setColumnStretch(3, 0)  # Кнопки [GET]

        # Начало отрезка
        start_label = QLabel("Начало:")
        start_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        start_label.setMinimumWidth(60)
        time_grid.addWidget(start_label, 0, 0)

        self.start_time_edit = QLineEdit()
        self.start_time_edit.setText(frames_to_time(self.marker.start_frame, self.fps))
        self.start_time_edit.textChanged.connect(self._update_start_frame_display)
        self.start_time_edit.editingFinished.connect(self._validate_start_time)
        self.start_time_edit.editingFinished.connect(self._seek_to_start_frame)
        time_grid.addWidget(self.start_time_edit, 0, 1)

        # Кнопки управления началом
        start_btn_layout = QHBoxLayout()
        start_btn_layout.setSpacing(2)
        start_minus_btn = QPushButton("-1")
        start_minus_btn.setMaximumWidth(30)
        start_minus_btn.setToolTip("Сдвинуть на 1 кадр назад (Shift+клик = 10 кадров)")
        start_minus_btn.clicked.connect(lambda: self._nudge_time(self.start_time_edit, -1))
        start_btn_layout.addWidget(start_minus_btn)

        start_plus_btn = QPushButton("+1")
        start_plus_btn.setMaximumWidth(30)
        start_plus_btn.setToolTip("Сдвинуть на 1 кадр вперед (Shift+клик = 10 кадров)")
        start_plus_btn.clicked.connect(lambda: self._nudge_time(self.start_time_edit, 1))
        start_btn_layout.addWidget(start_plus_btn)

        start_get_btn = QPushButton("⚓")
        start_get_btn.setMaximumWidth(30)
        start_get_btn.setToolTip("Взять время из плеера")
        start_get_btn.clicked.connect(lambda: self._get_time_from_player(self.start_time_edit))
        start_btn_layout.addWidget(start_get_btn)

        time_grid.addLayout(start_btn_layout, 0, 2)

        # Конец отрезка
        end_label = QLabel("Конец:")
        end_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        end_label.setMinimumWidth(60)
        time_grid.addWidget(end_label, 1, 0)

        self.end_time_edit = QLineEdit()
        self.end_time_edit.setText(frames_to_time(self.marker.end_frame, self.fps))
        self.end_time_edit.textChanged.connect(self._update_end_frame_display)
        self.end_time_edit.editingFinished.connect(self._validate_end_time)
        self.end_time_edit.editingFinished.connect(self._seek_to_end_frame)
        time_grid.addWidget(self.end_time_edit, 1, 1)

        # Кнопки управления концом
        end_btn_layout = QHBoxLayout()
        end_btn_layout.setSpacing(2)
        end_minus_btn = QPushButton("-1")
        end_minus_btn.setMaximumWidth(30)
        end_minus_btn.setToolTip("Сдвинуть на 1 кадр назад (Shift+клик = 10 кадров)")
        end_minus_btn.clicked.connect(lambda: self._nudge_time(self.end_time_edit, -1))
        end_btn_layout.addWidget(end_minus_btn)

        end_plus_btn = QPushButton("+1")
        end_plus_btn.setMaximumWidth(30)
        end_plus_btn.setToolTip("Сдвинуть на 1 кадр вперед (Shift+клик = 10 кадров)")
        end_plus_btn.clicked.connect(lambda: self._nudge_time(self.end_time_edit, 1))
        end_btn_layout.addWidget(end_plus_btn)

        end_get_btn = QPushButton("⚓")
        end_get_btn.setMaximumWidth(30)
        end_get_btn.setToolTip("Взять время из плеера")
        end_get_btn.clicked.connect(lambda: self._get_time_from_player(self.end_time_edit))
        end_btn_layout.addWidget(end_get_btn)

        time_grid.addLayout(end_btn_layout, 1, 2)

        # Длительность
        duration_label = QLabel("Длительность:")
        duration_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        duration_label.setMinimumWidth(60)
        time_grid.addWidget(duration_label, 2, 0)

        self.duration_edit = QLineEdit()
        self.duration_edit.setText(self._format_duration())
        self.duration_edit.textChanged.connect(self._update_duration_display)
        self.duration_edit.editingFinished.connect(self._validate_duration)
        time_grid.addWidget(self.duration_edit, 2, 1)

        layout.addLayout(time_grid)

        # Примечание
        note_layout = QHBoxLayout()
        note_label = QLabel("Примечание:")
        note_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        note_label.setMinimumWidth(80)
        self.note_edit = QLineEdit()
        self.note_edit.setText(self.marker.note or "")
        note_layout.addWidget(note_label)
        note_layout.addWidget(self.note_edit, 1)
        layout.addLayout(note_layout)

        # Разделитель
        layout.addSpacing(10)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Кнопка Сохранить (акцентная, зеленая)
        self.ok_btn = QPushButton("✓ Сохранить")
        self.ok_btn.setMaximumWidth(100)
        self.ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5016;
                color: white;
                border: 1px solid #3d6b1f;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d6b1f;
            }
            QPushButton:pressed {
                background-color: #1f3a0f;
            }
        """)
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)

        # Кнопка Отмена (контурная, серая)
        cancel_btn = QPushButton("✕ Отмена")
        cancel_btn.setMaximumWidth(100)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #cccccc;
                border: 1px solid #666666;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #333333;
                border-color: #888888;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        # Установить фокус
        self._set_initial_focus()

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
        return f"{minutes:02d}:{seconds:02d}"

    def _update_start_frame_display(self):
        """Обновить отображение начального кадра и длительности."""
        self._update_duration_from_times()

    def _update_end_frame_display(self):
        """Обновить отображение конечного кадра и длительности."""
        self._update_duration_from_times()

    def _update_duration_display(self):
        """Обновить длительность при изменении поля."""
        pass  # Длительность обновляется автоматически

    def _update_duration_from_times(self):
        """Обновить поле длительности на основе времени начала и конца."""
        duration_text = self._format_duration()
        self.duration_edit.blockSignals(True)
        self.duration_edit.setText(duration_text)
        self.duration_edit.blockSignals(False)
        self._validate_times()

    def _validate_start_time(self):
        """Валидация времени начала."""
        time_str = self.start_time_edit.text()
        if not validate_time_format(time_str):
            # Reset to previous valid value
            self.start_time_edit.setText(frames_to_time(self.marker.start_frame, self.fps))
        self._validate_times()

    def _validate_end_time(self):
        """Валидация времени конца."""
        time_str = self.end_time_edit.text()
        if not validate_time_format(time_str):
            # Reset to previous valid value
            self.end_time_edit.setText(frames_to_time(self.marker.end_frame, self.fps))
        self._validate_times()

    def _validate_duration(self):
        """Валидация длительности и обновление конца."""
        duration_str = self.duration_edit.text()
        try:
            # Парсим длительность
            if ':' in duration_str:
                parts = duration_str.split(':')
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    duration_secs = minutes * 60 + seconds
                else:
                    duration_secs = float(duration_str)
            else:
                duration_secs = float(duration_str)

            # Получить время начала
            start_frames = time_to_frames(self.start_time_edit.text(), self.fps)
            end_frames = start_frames + int(duration_secs * self.fps)

            # Обновить время конца
            end_time = frames_to_time(end_frames, self.fps)
            self.end_time_edit.blockSignals(True)
            self.end_time_edit.setText(end_time)
            self.end_time_edit.blockSignals(False)

            self._validate_times()

        except (ValueError, IndexError):
            # Reset to calculated duration
            self._update_duration_from_times()

    def _validate_times(self):
        """Проверить корректность временных границ."""
        start_frames = time_to_frames(self.start_time_edit.text(), self.fps)
        end_frames = time_to_frames(self.end_time_edit.text(), self.fps)

        is_valid = start_frames < end_frames

        # Обновить стили полей
        start_style = "QLineEdit { background-color: #333333; color: #ffffff; border: 1px solid #555555; }"
        end_style = "QLineEdit { background-color: #333333; color: #ffffff; border: 1px solid #555555; }"
        duration_style = "QLineEdit { background-color: #333333; color: #ffffff; border: 1px solid #555555; }"

        if not is_valid:
            start_style = "QLineEdit { background-color: #3d1a1a; color: #ffaaaa; border: 1px solid #ff5555; }"
            end_style = "QLineEdit { background-color: #3d1a1a; color: #ffaaaa; border: 1px solid #ff5555; }"
            duration_style = "QLineEdit { background-color: #3d1a1a; color: #ffaaaa; border: 1px solid #ff5555; }"

        self.start_time_edit.setStyleSheet(start_style)
        self.end_time_edit.setStyleSheet(end_style)
        self.duration_edit.setStyleSheet(duration_style)

        # Включить/отключить кнопку Сохранить
        self.ok_btn.setEnabled(is_valid)

    def _nudge_time(self, time_edit: QLineEdit, direction: int):
        """Сдвинуть время на N кадров."""
        # Проверить Shift для большего шага
        modifiers = QApplication.keyboardModifiers()
        step = 10 if (modifiers & Qt.KeyboardModifier.ShiftModifier) else 1

        current_frames = time_to_frames(time_edit.text(), self.fps)
        new_frames = current_frames + (direction * step)

        # Ограничить диапазон
        new_frames = max(0, new_frames)

        new_time = frames_to_time(new_frames, self.fps)
        time_edit.setText(new_time)

        # Seek к новому кадру
        if time_edit == self.start_time_edit:
            self._seek_to_start_frame()
        elif time_edit == self.end_time_edit:
            self._seek_to_end_frame()

    def _get_time_from_player(self, time_edit: QLineEdit):
        """Взять текущее время из плеера."""
        current_frame = self.video_controller.get_current_frame_idx()
        current_time = frames_to_time(current_frame, self.fps)
        time_edit.setText(current_time)

        # Seek к этому кадру
        if time_edit == self.start_time_edit:
            self._seek_to_start_frame()
        elif time_edit == self.end_time_edit:
            self._seek_to_end_frame()

    def _seek_to_start_frame(self):
        """Перемотать плеер к кадру начала."""
        start_frames = time_to_frames(self.start_time_edit.text(), self.fps)
        self.video_controller.seek_frame(start_frames)

    def _seek_to_end_frame(self):
        """Перемотать плеер к кадру конца."""
        end_frames = time_to_frames(self.end_time_edit.text(), self.fps)
        self.video_controller.seek_frame(end_frames)

    def _set_initial_focus(self):
        """Установить начальный фокус."""
        # Если время уже установлено (не по умолчанию), фокус на примечание
        # Иначе на тип события
        if (self.marker.start_frame > 0 or self.marker.end_frame > 0 or
            self.marker.note):
            self.note_edit.setFocus()
        else:
            self.type_combo.setFocus()

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
