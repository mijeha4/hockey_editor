from PySide6.QtCore import QObject, Signal
from typing import Optional
from enum import Enum
from ..models.marker import Marker
from ..utils.settings_manager import get_settings_manager
from ..utils.custom_events import get_custom_event_manager


class RecordingMode(Enum):
    """Режимы расстановки отрезков."""
    DYNAMIC = "dynamic"          # Два нажатия = начало и конец
    FIXED_LENGTH = "fixed_length"  # Одно нажатие = отрезок фиксированной длины


class EventCreationController(QObject):
    """Контроллер создания событий (отрезков)."""

    # Сигналы
    recording_status_changed = Signal(str, str)  # event_type (A/D/S), status (Recording/Complete)
    markers_changed = Signal()
    timeline_update = Signal()

    def __init__(self, video_controller):
        super().__init__()
        self.video_controller = video_controller
        self.settings = get_settings_manager()
        self.event_manager = get_custom_event_manager()

        # Параметры расстановки отрезков (загрузить из QSettings)
        mode_str = self.settings.load_recording_mode()
        self.recording_mode = RecordingMode(mode_str)
        self.fixed_duration_sec = self.settings.load_fixed_duration()
        self.pre_roll_sec = self.settings.load_pre_roll()
        self.post_roll_sec = self.settings.load_post_roll()

        # Состояние текущей записи
        self.is_recording = False
        self.recording_event_name: Optional[str] = None  # Имя события вместо EventType
        self.recording_start_frame: Optional[int] = None

    def on_hotkey_pressed(self, key: str):
        """Обработка нажатия горячей клавиши для создания события."""
        # Найти событие по клавише
        event = self.event_manager.get_event_by_hotkey(key)
        if not event:
            return  # Нет события для этой клавиши

        current_frame = self.video_controller.get_current_frame_idx()
        event_name = event.name

        if self.recording_mode == RecordingMode.DYNAMIC:
            self._handle_dynamic_mode(event_name, current_frame)
        elif self.recording_mode == RecordingMode.FIXED_LENGTH:
            self._handle_fixed_length_mode(event_name, current_frame)

    def _handle_dynamic_mode(self, event_name: str, current_frame: int):
        """Динамический режим: два нажатия = начало и конец."""
        if not self.is_recording:
            # Начало записи
            self.is_recording = True
            self.recording_event_name = event_name
            self.recording_start_frame = current_frame
            self.recording_status_changed.emit(event_name, "Recording")
            self.timeline_update.emit()
        elif self.recording_event_name == event_name:
            # Конец записи
            pre_roll_frames = max(0, int(self.pre_roll_sec * self.video_controller.get_fps()))
            start_frame = max(0, self.recording_start_frame - pre_roll_frames)

            marker = Marker(
                start_frame=start_frame,
                end_frame=current_frame,
                event_name=event_name,
                note=""
            )
            self.video_controller.markers.append(marker)

            # Автооткат начала отрезка
            self.video_controller.seek_frame(start_frame)

            self.is_recording = False
            self.recording_event_name = None
            self.recording_start_frame = None

            self.recording_status_changed.emit(event_name, "Complete")
            self.markers_changed.emit()
            self.timeline_update.emit()

    def _handle_fixed_length_mode(self, event_name: str, current_frame: int):
        """Фиксированная длина: одно нажатие = отрезок фиксированной длины."""
        # Рассчитать границы
        fixed_frames = int(self.fixed_duration_sec * self.video_controller.get_fps())
        pre_roll_frames = max(0, int(self.pre_roll_sec * self.video_controller.get_fps()))

        start_frame = max(0, current_frame - pre_roll_frames)
        end_frame = min(self.video_controller.get_total_frames() - 1, current_frame + fixed_frames - pre_roll_frames)

        # Создать отрезок
        marker = Marker(
            start_frame=start_frame,
            end_frame=end_frame,
            event_name=event_name,
            note=""
        )
        self.video_controller.markers.append(marker)

        # Визуальная обратная связь
        self.recording_status_changed.emit(event_name, "Fixed")

        # Автооткат начала отрезка
        self.video_controller.seek_frame(start_frame)

        self.markers_changed.emit()
        self.timeline_update.emit()

    def cancel_recording(self):
        """Отменить текущую запись."""
        if self.is_recording:
            self.is_recording = False
            self.recording_event_name = None
            self.recording_start_frame = None
            self.recording_status_changed.emit("", "Cancelled")
            self.timeline_update.emit()

    def set_recording_mode(self, mode):
        """Установить режим расстановки отрезков."""
        self.recording_mode = mode
        self.settings.save_recording_mode(mode.value)

    def set_fixed_duration(self, seconds: int):
        """Установить фиксированную длину отрезка."""
        self.fixed_duration_sec = seconds
        self.settings.save_fixed_duration(seconds)

    def set_pre_roll(self, seconds: float):
        """Установить откат перед началом отрезка."""
        self.pre_roll_sec = seconds
        self.settings.save_pre_roll(seconds)

    def set_post_roll(self, seconds: float):
        """Установить добавление в конец отрезка."""
        self.post_roll_sec = seconds
        self.settings.save_post_roll(seconds)
