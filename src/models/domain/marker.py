from typing import Dict, Any
from PySide6.QtCore import QObject, Signal


class Marker(QObject):
    """Модель маркера события в видео с реактивностью PySide6."""

    # Сигналы
    changed = Signal()  # Любые изменения
    position_changed = Signal(int, int)  # start_frame, end_frame
    name_changed = Signal(str)  # event_name
    note_changed = Signal(str)  # note

    def __init__(self, start_frame: int, end_frame: int, event_name: str, note: str = ""):
        super().__init__()
        self._start_frame = start_frame
        self._end_frame = end_frame
        self._event_name = event_name
        self._note = note

    @property
    def start_frame(self) -> int:
        return self._start_frame

    @start_frame.setter
    def start_frame(self, value: int):
        if self._start_frame != value:
            self._start_frame = value
            self.position_changed.emit(self._start_frame, self._end_frame)
            self.changed.emit()

    @property
    def end_frame(self) -> int:
        return self._end_frame

    @end_frame.setter
    def end_frame(self, value: int):
        if self._end_frame != value:
            self._end_frame = value
            self.position_changed.emit(self._start_frame, self._end_frame)
            self.changed.emit()

    @property
    def event_name(self) -> str:
        return self._event_name

    @event_name.setter
    def event_name(self, value: str):
        if self._event_name != value:
            self._event_name = value
            self.name_changed.emit(self._event_name)
            self.changed.emit()

    @property
    def note(self) -> str:
        return self._note

    @note.setter
    def note(self, value: str):
        if self._note != value:
            self._note = value
            self.note_changed.emit(self._note)
            self.changed.emit()

    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь для сериализации."""
        return {
            "start_frame": self._start_frame,
            "end_frame": self._end_frame,
            "event_name": self._event_name,
            "note": self._note
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Marker':
        """Создать из словаря."""
        return cls(
            start_frame=data["start_frame"],
            end_frame=data["end_frame"],
            event_name=data.get("event_name", "Attack"),
            note=data.get("note", "")
        )

    def to_marker(self) -> 'Marker':
        """Вернуть копию маркера для совместимости."""
        return Marker(
            start_frame=self.start_frame,
            end_frame=self.end_frame,
            event_name=self.event_name,
            note=self.note
        )
