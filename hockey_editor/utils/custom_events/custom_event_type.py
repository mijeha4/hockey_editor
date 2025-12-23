from typing import Dict
from dataclasses import dataclass
from PySide6.QtGui import QColor


@dataclass
class CustomEventType:
    """Represents a custom event type with metadata."""

    name: str
    color: str  # Hex color (e.g., "#FF0000")
    shortcut: str = ""  # Keyboard shortcut (e.g., "A", "Ctrl+X")
    description: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'color': self.color,
            'shortcut': self.shortcut,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'CustomEventType':
        """Create from dictionary (deserialization)."""
        return cls(
            name=data.get('name', ''),
            color=data.get('color', '#CCCCCC'),
            shortcut=data.get('shortcut', ''),
            description=data.get('description', '')
        )

    def get_qcolor(self) -> QColor:
        """Get Qt color object."""
        color = QColor(self.color)
        return color if color.isValid() else QColor('#CCCCCC')

    def get_localized_name(self) -> str:
        """Get localized name for the event (hardcoded Russian for default events)."""
        # Hardcoded Russian translations for default events
        name_map = {
            'Goal': 'Гол',
            'Shot on Goal': 'Бросок в створ',
            'Missed Shot': 'Бросок мимо',
            'Blocked Shot': 'Заблокированный бросок',
            'Zone Entry': 'Вход в зону',
            'Zone Exit': 'Выход из зоны',
            'Dump In': 'Вброс',
            'Turnover': 'Потеря',
            'Takeaway': 'Перехват',
            'Faceoff Win': 'Вбрасывание: Победа',
            'Faceoff Loss': 'Вбрасывание: Поражение',
            'Defensive Block': 'Блокшот в обороне',
            'Penalty': 'Удаление'
        }

        # Return Russian name if it's a default event, otherwise return original name
        return name_map.get(self.name, self.name)

    def get_localized_description(self) -> str:
        """Get localized description for the event (hardcoded Russian for default events)."""
        # Hardcoded Russian descriptions for default events
        desc_map = {
            'Goal': 'Забитый гол',
            'Shot on Goal': 'Бросок в створ ворот',
            'Missed Shot': 'Бросок мимо ворот',
            'Blocked Shot': 'Бросок заблокирован',
            'Zone Entry': 'Вход в зону атаки',
            'Zone Exit': 'Выход из зоны защиты',
            'Dump In': 'Вброс шайбы в зону',
            'Turnover': 'Потеря владения шайбой',
            'Takeaway': 'Перехват шайбы',
            'Faceoff Win': 'Выигранное вбрасывание',
            'Faceoff Loss': 'Проигранное вбрасывание',
            'Defensive Block': 'Блокшот в обороне',
            'Penalty': 'Назначенное удаление'
        }

        # Return Russian description if it's a default event, otherwise return original description
        return desc_map.get(self.name, self.description)
