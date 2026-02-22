from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from PySide6.QtGui import QColor


@dataclass(frozen=True)
class CustomEventType:
    """Represents an event type with metadata."""

    name: str
    color: str                   # "#RRGGBB"
    shortcut: str = ""           # e.g. "A", "Ctrl+X"
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "color": self.color,
            "shortcut": self.shortcut,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CustomEventType":
        return cls(
            name=str(data.get("name", "")).strip(),
            color=str(data.get("color", "#CCCCCC")).strip(),
            shortcut=str(data.get("shortcut", "")).strip(),
            description=str(data.get("description", "")).strip(),
        )

    def get_qcolor(self) -> QColor:
        c = QColor(self.color)
        return c if c.isValid() else QColor("#CCCCCC")

    def get_localized_name(self) -> str:
        name_map = {
            "Goal": "Гол",
            "Shot on Goal": "Бросок в створ",
            "Missed Shot": "Бросок мимо",
            "Blocked Shot": "Заблокированный бросок",
            "Zone Entry": "Вход в зону",
            "Zone Exit": "Выход из зоны",
            "Dump In": "Вброс",
            "Turnover": "Потеря",
            "Takeaway": "Перехват",
            "Faceoff Win": "Вбрасывание: Победа",
            "Faceoff Loss": "Вбрасывание: Поражение",
            "Defensive Block": "Блокшот в обороне",
            "Penalty": "Удаление",
        }
        return name_map.get(self.name, self.name)

    def get_localized_description(self) -> str:
        desc_map = {
            "Goal": "Забитый гол",
            "Shot on Goal": "Бросок в створ ворот",
            "Missed Shot": "Бросок мимо ворот",
            "Blocked Shot": "Бросок заблокирован",
            "Zone Entry": "Вход в зону атаки",
            "Zone Exit": "Выход из зоны защиты",
            "Dump In": "Вброс шайбы в зону",
            "Turnover": "Потеря владения шайбой",
            "Takeaway": "Перехват шайбы",
            "Faceoff Win": "Выигранное вбрасывание",
            "Faceoff Loss": "Проигранное вбрасывание",
            "Defensive Block": "Блокшот в обороне",
            "Penalty": "Назначенное удаление",
        }
        return desc_map.get(self.name, self.description)