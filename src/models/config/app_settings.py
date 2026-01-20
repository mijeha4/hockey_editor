from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum


class Theme(Enum):
    """Available UI themes."""
    DARK = "dark"
    LIGHT = "light"


class RecordingMode(Enum):
    """Режимы расстановки маркеров."""
    DYNAMIC = "dynamic"          # Два нажатия = начало и конец
    FIXED_LENGTH = "fixed_length"  # Одно нажатие = отрезок фиксированной длины


@dataclass
class EventType:
    """Тип события с настройками."""
    name: str
    color: str
    shortcut: str
    description: str = ""


@dataclass
class AppSettings:
    """Модель настроек приложения."""

    # Список событий по умолчанию (13 штук)
    default_events: List[EventType] = field(default_factory=lambda: [
        # Shooting
        EventType(name='Goal', color='#FF0000', shortcut='G', description='Goal scored'),
        EventType(name='Shot on Goal', color='#FF5722', shortcut='H', description='Shot on goal'),
        EventType(name='Missed Shot', color='#FF9800', shortcut='M', description='Shot missed the net'),
        EventType(name='Blocked Shot', color='#795548', shortcut='B', description='Shot blocked'),

        # Zone Entries/Exits
        EventType(name='Zone Entry', color='#2196F3', shortcut='Z', description='Entry into offensive zone'),
        EventType(name='Zone Exit', color='#03A9F4', shortcut='X', description='Exit from defensive zone'),
        EventType(name='Dump In', color='#00BCD4', shortcut='D', description='Dump puck into zone'),

        # Possession
        EventType(name='Turnover', color='#607D8B', shortcut='T', description='Loss of puck possession'),
        EventType(name='Takeaway', color='#4CAF50', shortcut='A', description='Puck possession gained'),
        EventType(name='Faceoff Win', color='#8BC34A', shortcut='F', description='Faceoff won'),
        EventType(name='Faceoff Loss', color='#558B2F', shortcut='L', description='Faceoff lost'),

        # Defense
        EventType(name='Defensive Block', color='#3F51B5', shortcut='K', description='Shot blocked in defense'),
        EventType(name='Penalty', color='#9C27B0', shortcut='P', description='Penalty called'),
    ])

    # Горячие клавиши
    hotkeys: Dict[str, str] = field(default_factory=lambda: {
        'ATTACK': 'A', 'DEFENSE': 'D', 'SHIFT': 'S'
    })

    # Режим расстановки
    recording_mode: str = "dynamic"
    fixed_duration_sec: int = 10
    pre_roll_sec: float = 3.0
    post_roll_sec: float = 0.0

    # Цвета дорожек
    track_colors: Dict[str, str] = field(default_factory=lambda: {
        'ATTACK': '#8b0000',    # Тёмно-красный
        'DEFENSE': '#000080',   # Тёмно-синий
        'SHIFT': '#006400',     # Тёмно-зелёный
    })

    # Размер и позиция окна
    window_x: int = 0
    window_y: int = 0
    window_width: int = 1800
    window_height: int = 1000

    # Автосохранение
    autosave_enabled: bool = True
    autosave_interval_minutes: int = 5

    # Последние открытые файлы
    recent_projects: List[str] = field(default_factory=list)

    # Пользовательские события
    custom_events: List[Dict] = field(default_factory=list)

    # Язык
    language: str = "ru"

    # Скорость воспроизведения
    playback_speed: float = 1.0

    # Тема интерфейса
    theme: str = Theme.DARK.value

    def to_dict(self) -> Dict:
        """Конвертировать в словарь."""
        return {
            'hotkeys': self.hotkeys,
            'recording_mode': self.recording_mode,
            'fixed_duration_sec': self.fixed_duration_sec,
            'pre_roll_sec': self.pre_roll_sec,
            'post_roll_sec': self.post_roll_sec,
            'track_colors': self.track_colors,
            'window_x': self.window_x,
            'window_y': self.window_y,
            'window_width': self.window_width,
            'window_height': self.window_height,
            'autosave_enabled': self.autosave_enabled,
            'autosave_interval_minutes': self.autosave_interval_minutes,
            'recent_projects': self.recent_projects,
            'custom_events': self.custom_events,
            'language': self.language,
            'playback_speed': self.playback_speed,
            'theme': self.theme,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'AppSettings':
        """Создать из словаря."""
        return cls(
            hotkeys=data.get('hotkeys', cls.hotkeys),
            recording_mode=data.get('recording_mode', cls.recording_mode),
            fixed_duration_sec=data.get('fixed_duration_sec', cls.fixed_duration_sec),
            pre_roll_sec=data.get('pre_roll_sec', cls.pre_roll_sec),
            post_roll_sec=data.get('post_roll_sec', cls.post_roll_sec),
            track_colors=data.get('track_colors', cls.track_colors),
            window_x=data.get('window_x', cls.window_x),
            window_y=data.get('window_y', cls.window_y),
            window_width=data.get('window_width', cls.window_width),
            window_height=data.get('window_height', cls.window_height),
            autosave_enabled=data.get('autosave_enabled', cls.autosave_enabled),
            autosave_interval_minutes=data.get('autosave_interval_minutes', cls.autosave_interval_minutes),
            recent_projects=data.get('recent_projects', cls.recent_projects),
            custom_events=data.get('custom_events', cls.custom_events),
            language=data.get('language', cls.language),
            playback_speed=data.get('playback_speed', cls.playback_speed),
            theme=data.get('theme', cls.theme),
        )
