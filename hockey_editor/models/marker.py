from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    ATTACK = "Атака"
    DEFENSE = "Защита"
    SHIFT = "Смена"

@dataclass
class Marker:
    frame: int
    type: EventType
    note: str = ""

    def to_dict(self):
        return {"frame": self.frame, "type": self.type.value, "note": self.note}

    @classmethod
    def from_dict(cls, data):
        return cls(
            frame=data["frame"],
            type=EventType(data["type"]),
            note=data.get("note", "")
        )