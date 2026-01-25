"""
Settings Manager - сервис для загрузки и сохранения настроек приложения.

Отвечает за сериализацию/десериализацию настроек в JSON формате.
"""

import json
import os
from typing import Dict, List, Optional

from models.config.app_settings import AppSettings


# Global instance
_settings_manager: Optional['SettingsManager'] = None


def get_settings_manager() -> 'SettingsManager':
    """Get or create global SettingsManager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


class SettingsManager:
    """Сервис для загрузки и сохранения настроек приложения."""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path

    def load_settings(self) -> Optional[AppSettings]:
        """Загрузить настройки из файла."""
        if not os.path.exists(self.config_path):
            return None

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Создаем объект настроек из словаря
            return AppSettings.from_dict(data)

        except Exception as e:
            print(f"Error loading settings: {e}")
            return None

    def save_settings(self, settings: AppSettings) -> bool:
        """Сохранить настройки в файл."""
        try:
            # Преобразуем объект настроек в словарь
            data = settings.to_dict()

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True

        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def export_settings(self, settings: AppSettings, file_path: str) -> bool:
        """Экспортировать настройки в указанный файл."""
        try:
            data = settings.to_dict()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False

    def import_settings(self, file_path: str) -> Optional[AppSettings]:
        """Импортировать настройки из файла."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return AppSettings.from_dict(data)
        except Exception as e:
            print(f"Error importing settings: {e}")
            return None

    def load_custom_events(self) -> List[Dict]:
        """Load custom events from settings."""
        settings = self.load_settings()
        if settings:
            return settings.custom_events
        return []

    def save_custom_events(self, events_data: List[Dict]) -> None:
        """Save custom events to settings."""
        settings = self.load_settings() or AppSettings()
        settings.custom_events = events_data
        self.save_settings(settings)
