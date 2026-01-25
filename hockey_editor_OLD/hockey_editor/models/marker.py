from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    """Устаревший enum - для backwards compatibility."""
    ATTACK = "Атака"
    DEFENSE = "Защита"
    SHIFT = "Смена"

@dataclass
class Marker:
    start_frame: int
    end_frame: int
    event_name: str  # Новое поле: имя события (например, "Attack", "Defense", "MyCustomEvent")
    note: str = ""

    def to_dict(self):
        return {
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "event_name": self.event_name,  # Сохраняем имя события
            "note": self.note
        }

    @classmethod
    def from_dict(cls, data):
        # Backwards compatibility: если есть поле "type" вместо "event_name"
        if "type" in data and "event_name" not in data:
            # Конвертировать старый enum value в имя события
            event_type_value = data["type"]
            # Маппинг старых значений на имена
            type_to_name = {
                "Атака": "Attack",
                "Защита": "Defense",
                "Смена": "Shift"
            }
            event_name = type_to_name.get(event_type_value, event_type_value)
        else:
            event_name = data.get("event_name", "Attack")  # Default to Attack

        return cls(
            start_frame=data["start_frame"],
            end_frame=data["end_frame"],
            event_name=event_name,
            note=data.get("note", "")
        )
