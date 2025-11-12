from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    ATTACK = "Атака"
    DEFENSE = "Защита"
    SHIFT = "Смена"

@dataclass
class Marker:
    start_frame: int
    end_frame: int
    type: EventType
    note: str = ""

    def to_dict(self):
        return {
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "type": self.type.value,
            "note": self.note
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            start_frame=data["start_frame"],
            end_frame=data["end_frame"],
            type=EventType(data["type"]),
            note=data.get("note", "")
        )