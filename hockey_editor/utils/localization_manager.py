"""
LocalizationManager - класс для управления локализацией (многоязыковой поддержкой).
Загружает переводы из JSON файлов и предоставляет методы для перевода текста.
"""

import json
import os
from PySide6.QtCore import QObject, Signal
from typing import Dict, Optional
from .settings_manager import get_settings_manager


class LocalizationManager(QObject):
    """
    Менеджер локализации на основе JSON файлов.
    Поддерживает переключение языков без перезапуска приложения.
    """

    # Сигнал, испускаемый при изменении языка
    language_changed = Signal(str)  # новый язык (например, "en" или "ru")

    def __init__(self):
        super().__init__()
        self._current_language = "ru"  # По умолчанию русский
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()

        # Загружаем сохраненный язык из настроек
        settings_manager = get_settings_manager()
        saved_language = settings_manager.load_language()
        if saved_language in self._translations:
            self._current_language = saved_language

    def _load_translations(self) -> None:
        """Загрузить переводы из JSON файлов."""
        locales_dir = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "locales")

        # Загружаем английские переводы (обязательно)
        en_path = os.path.join(locales_dir, "en.json")
        if os.path.exists(en_path):
            with open(en_path, 'r', encoding='utf-8') as f:
                self._translations["en"] = json.load(f)

        # Загружаем русские переводы (обязательно)
        ru_path = os.path.join(locales_dir, "ru.json")
        if os.path.exists(ru_path):
            with open(ru_path, 'r', encoding='utf-8') as f:
                self._translations["ru"] = json.load(f)

        # Если английские переводы не загружены, создаем пустой словарь
        if "en" not in self._translations:
            self._translations["en"] = {}

        # Если русские переводы не загружены, создаем пустой словарь
        if "ru" not in self._translations:
            self._translations["ru"] = {}

    def get_available_languages(self) -> list:
        """Получить список доступных языков."""
        return list(self._translations.keys())

    def get_current_language(self) -> str:
        """Получить текущий язык."""
        return self._current_language

    def set_language(self, language: str) -> bool:
        """
        Установить новый язык.
        Возвращает True если язык был изменен, False если остался прежним или не найден.
        """
        if language not in self._translations:
            return False

        if language == self._current_language:
            return False

        old_language = self._current_language
        self._current_language = language

        # Сохраняем выбор языка в настройках
        settings_manager = get_settings_manager()
        settings_manager.save_language(language)

        # Испускаем сигнал об изменении языка
        self.language_changed.emit(language)

        return True

    def tr(self, key: str, default: str = "") -> str:
        """
        Получить перевод для ключа.
        Если перевод не найден, возвращает default или сам ключ.
        """
        if self._current_language in self._translations:
            translations = self._translations[self._current_language]
            if key in translations:
                return translations[key]

        # Fallback к английскому
        if "en" in self._translations and key in self._translations["en"]:
            return self._translations["en"][key]

        # Если ничего не найдено, возвращаем default или ключ
        return default if default else key

    def get_language_display_name(self, language_code: str) -> str:
        """Получить отображаемое имя языка."""
        names = {
            "en": "English",
            "ru": "Русский"
        }
        return names.get(language_code, language_code)


# Глобальный экземпляр LocalizationManager
_localization_manager_instance: Optional[LocalizationManager] = None


def get_localization_manager() -> LocalizationManager:
    """Получить глобальный экземпляр LocalizationManager."""
    global _localization_manager_instance
    if _localization_manager_instance is None:
        _localization_manager_instance = LocalizationManager()
    return _localization_manager_instance
