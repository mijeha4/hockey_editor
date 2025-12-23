from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class EventType:
    """Модель типа события."""

    name: str
    color: str  # Hex color (e.g., "#FF0000")
    shortcut: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь для сериализации."""
        return {
            'name': self.name,
            'color': self.color,
            'shortcut': self.shortcut,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventType':
        """Создать из словаря."""
        return cls(
            name=data.get('name', ''),
            color=data.get('color', '#CCCCCC'),
            shortcut=data.get('shortcut', ''),
            description=data.get('description', '')
        )

    def get_localized_name(self) -> str:
        """Получить локализованное имя события."""
        # Хардкод русские переводы для стандартных событий
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
        return name_map.get(self.name, self.name)

    def get_localized_description(self) -> str:
        """Получить локализованное описание события."""
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
        return desc_map.get(self.name, self.description)
