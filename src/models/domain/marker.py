from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Marker:
    """Модель маркера события в видео."""

    start_frame: int
    end_frame: int
    event_name: str  # Имя события (например, "Attack", "Defense", "MyCustomEvent")
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь для сериализации."""
        return {
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "event_name": self.event_name,
            "note": self.note
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
