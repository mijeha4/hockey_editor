"""
SettingsManager - класс для управления всеми настройками через QSettings.
Сохраняет и загружает: горячие клавиши, режимы, цвета, размер окна, etc.
"""

from PySide6.QtCore import QSettings
from typing import Dict, Tuple, Optional
from enum import Enum


class SettingsManager:
    """
    Менеджер настроек на основе QSettings (реестр Windows / конфиг Linux).
    Организованы по группам: hotkeys, ui, recording, colors, autosave.
    """
    
    def __init__(self, org: str = "HockeyEditorPro", app: str = "HockeyEditor"):
        """Инициализировать QSettings."""
        self.settings = QSettings(org, app)
    
    # ============= ГОРЯЧИЕ КЛАВИШИ =============
    
    def save_hotkeys(self, hotkeys: Dict[str, str]) -> None:
        """
        Сохранить горячие клавиши.
        Пример: {'ATTACK': 'A', 'DEFENSE': 'D', 'SHIFT': 'S'}
        """
        self.settings.beginGroup("hotkeys")
        for event_type, key in hotkeys.items():
            self.settings.setValue(event_type, key)
        self.settings.endGroup()
    
    def load_hotkeys(self) -> Dict[str, str]:
        """
        Загрузить горячие клавиши.
        Возвращает дефолтные, если не найдены.
        """
        default = {'ATTACK': 'A', 'DEFENSE': 'D', 'SHIFT': 'S'}
        self.settings.beginGroup("hotkeys")
        hotkeys = {k: self.settings.value(k, v) for k, v in default.items()}
        self.settings.endGroup()
        return hotkeys
    
    # ============= РЕЖИМ РАССТАНОВКИ =============
    
    def save_recording_mode(self, mode: str) -> None:
        """Сохранить режим расстановки: 'dynamic' или 'fixed_length'."""
        self.settings.setValue("recording/mode", mode)
    
    def load_recording_mode(self) -> str:
        """Загрузить режим расстановки (по умолчанию 'dynamic')."""
        return self.settings.value("recording/mode", "dynamic")
    
    def save_fixed_duration(self, seconds: int) -> None:
        """Сохранить фиксированную длину отрезка (в секундах)."""
        self.settings.setValue("recording/fixed_duration_sec", seconds)
    
    def load_fixed_duration(self) -> int:
        """Загрузить фиксированную длину отрезка (по умолчанию 10)."""
        return int(self.settings.value("recording/fixed_duration_sec", 10))
    
    def save_pre_roll(self, seconds: float) -> None:
        """Сохранить откат перед началом отрезка (в секундах)."""
        self.settings.setValue("recording/pre_roll_sec", seconds)
    
    def load_pre_roll(self) -> float:
        """Загрузить откат перед началом отрезка (по умолчанию 3.0)."""
        return float(self.settings.value("recording/pre_roll_sec", 3.0))
    
    def save_post_roll(self, seconds: float) -> None:
        """Сохранить добавление в конец отрезка (в секундах)."""
        self.settings.setValue("recording/post_roll_sec", seconds)
    
    def load_post_roll(self) -> float:
        """Загрузить добавление в конец отрезка (по умолчанию 0.0)."""
        return float(self.settings.value("recording/post_roll_sec", 0.0))
    
    # ============= ЦВЕТА ДОРОЖЕК =============
    
    def save_track_colors(self, colors: Dict[str, str]) -> None:
        """
        Сохранить цвета дорожек.
        Пример: {'ATTACK': '#8b0000', 'DEFENSE': '#000080', 'SHIFT': '#006400'}
        """
        self.settings.beginGroup("colors")
        for track, hex_color in colors.items():
            self.settings.setValue(track, hex_color)
        self.settings.endGroup()
    
    def load_track_colors(self) -> Dict[str, str]:
        """Загрузить цвета дорожек (вернёт дефолтные, если не найдены)."""
        default = {
            'ATTACK': '#8b0000',    # Тёмно-красный
            'DEFENSE': '#000080',   # Тёмно-синий
            'SHIFT': '#006400',     # Тёмно-зелёный
        }
        self.settings.beginGroup("colors")
        colors = {k: self.settings.value(k, v) for k, v in default.items()}
        self.settings.endGroup()
        return colors
    
    # ============= РАЗМЕР И ПОЗИЦИЯ ОКНА =============
    
    def save_window_geometry(self, x: int, y: int, width: int, height: int) -> None:
        """Сохранить размер и позицию главного окна."""
        self.settings.beginGroup("ui")
        self.settings.setValue("window_x", x)
        self.settings.setValue("window_y", y)
        self.settings.setValue("window_width", width)
        self.settings.setValue("window_height", height)
        self.settings.endGroup()
    
    def load_window_geometry(self) -> Tuple[int, int, int, int]:
        """
        Загрузить размер и позицию окна.
        Возвращает (x, y, width, height) или дефолтные значения.
        """
        self.settings.beginGroup("ui")
        x = int(self.settings.value("window_x", 0))
        y = int(self.settings.value("window_y", 0))
        width = int(self.settings.value("window_width", 1800))
        height = int(self.settings.value("window_height", 1000))
        self.settings.endGroup()
        return x, y, width, height
    
    # ============= АВТОСОХРАНЕНИЕ =============
    
    def save_autosave_enabled(self, enabled: bool) -> None:
        """Сохранить включено ли автосохранение."""
        self.settings.setValue("autosave/enabled", enabled)
    
    def load_autosave_enabled(self) -> bool:
        """Загрузить статус автосохранения (по умолчанию True)."""
        return self.settings.value("autosave/enabled", True, type=bool)
    
    def save_autosave_interval(self, minutes: int) -> None:
        """Сохранить интервал автосохранения (в минутах)."""
        self.settings.setValue("autosave/interval_minutes", minutes)
    
    def load_autosave_interval(self) -> int:
        """Загрузить интервал автосохранения (по умолчанию 5 минут)."""
        return int(self.settings.value("autosave/interval_minutes", 5))
    
    # ============= ПОСЛЕДНИЕ ОТКРЫТЫЕ ФАЙЛЫ =============
    
    def save_recent_projects(self, project_paths: list) -> None:
        """Сохранить список последних открытых проектов (до 10)."""
        self.settings.beginGroup("recent")
        for i, path in enumerate(project_paths[:10]):
            self.settings.setValue(f"project_{i}", path)
        self.settings.endGroup()
    
    def load_recent_projects(self) -> list:
        """Загрузить список последних открытых проектов."""
        self.settings.beginGroup("recent")
        projects = []
        for i in range(10):
            path = self.settings.value(f"project_{i}")
            if path:
                projects.append(path)
        self.settings.endGroup()
        return projects
    
    def add_recent_project(self, project_path: str) -> None:
        """Добавить проект в список недавних."""
        recent = self.load_recent_projects()
        if project_path in recent:
            recent.remove(project_path)
        recent.insert(0, project_path)
        self.save_recent_projects(recent)
    
    # ============= ПОЛЬЗОВАТЕЛЬСКИЕ СОБЫТИЯ =============
    
    def save_custom_events(self, events_data: list) -> None:
        """
        Сохранить пользовательские события.
        events_data: List[{'name': str, 'color': str, 'shortcut': str, 'description': str}]
        """
        self.settings.beginGroup("custom_events")
        self.settings.remove("")  # Очистить старые значения
        for idx, event_dict in enumerate(events_data):
            event_str = str(event_dict)  # Сохранить как строку
            self.settings.setValue(f"event_{idx}", event_str)
        self.settings.endGroup()
    
    def load_custom_events(self) -> list:
        """Загрузить пользовательские события."""
        import ast
        self.settings.beginGroup("custom_events")
        keys = self.settings.childKeys()
        events = []
        for key in sorted(keys):
            event_str = self.settings.value(key)
            if event_str:
                try:
                    event_dict = ast.literal_eval(event_str)
                    events.append(event_dict)
                except (ValueError, SyntaxError):
                    pass
        self.settings.endGroup()
        return events
    
    # ============= СЛУЖЕБНЫЕ МЕТОДЫ =============
    
    def clear_all(self) -> None:
        """Очистить все настройки."""
        self.settings.clear()
    
    def sync(self) -> None:
        """Синхронизировать настройки с хранилищем."""
        self.settings.sync()


# Глобальный экземпляр SettingsManager
_settings_manager_instance: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Получить глобальный экземпляр SettingsManager."""
    global _settings_manager_instance
    if _settings_manager_instance is None:
        _settings_manager_instance = SettingsManager()
    return _settings_manager_instance
