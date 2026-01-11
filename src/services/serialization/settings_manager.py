"""
Settings Manager - сервис для загрузки и сохранения настроек приложения.

Отвечает за сериализацию/десериализацию настроек в JSON формате.
"""

import json
import os
from typing import Optional

from models.config.app_settings import AppSettings


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
