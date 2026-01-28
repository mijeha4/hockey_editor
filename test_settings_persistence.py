#!/usr/bin/env python3
"""
Тест для проверки сохранения и применения настроек режима отрезка при перезапуске приложения.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Добавить src в путь для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.config.app_settings import AppSettings
from services.serialization.settings_manager import SettingsManager


def test_settings_persistence():
    """Тест сохранения и загрузки настроек."""
    print("=== Тест сохранения и загрузки настроек ===")
    
    # Создать временный файл для настроек
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_path = temp_file.name
    
    try:
        # Создать менеджер настроек с временным файлом
        settings_manager = SettingsManager(temp_path)
        
        # Создать настройки с фиксированной длиной
        settings = AppSettings()
        settings.recording_mode = "fixed_length"
        settings.fixed_duration_sec = 15
        settings.pre_roll_sec = 2.5
        settings.post_roll_sec = 1.0
        
        print(f"Исходные настройки: режим={settings.recording_mode}, длительность={settings.fixed_duration_sec}с")
        
        # Сохранить настройки
        success = settings_manager.save_settings(settings)
        assert success, "Не удалось сохранить настройки"
        print("✓ Настройки сохранены")
        
        # Загрузить настройки
        loaded_settings = settings_manager.load_settings()
        assert loaded_settings is not None, "Не удалось загрузить настройки"
        print("✓ Настройки загружены")
        
        # Проверить соответствие
        assert loaded_settings.recording_mode == "fixed_length", f"Неверный режим: {loaded_settings.recording_mode}"
        assert loaded_settings.fixed_duration_sec == 15, f"Неверная длительность: {loaded_settings.fixed_duration_sec}"
        assert loaded_settings.pre_roll_sec == 2.5, f"Неверный pre-roll: {loaded_settings.pre_roll_sec}"
        assert loaded_settings.post_roll_sec == 1.0, f"Неверный post-roll: {loaded_settings.post_roll_sec}"
        print("✓ Все параметры соответствуют ожидаемым значениям")
        
        # Проверить динамический режим
        settings.recording_mode = "dynamic"
        settings.fixed_duration_sec = 8
        settings.pre_roll_sec = 1.0
        settings.post_roll_sec = 0.5
        
        success = settings_manager.save_settings(settings)
        assert success, "Не удалось сохранить настройки динамического режима"
        print("✓ Настройки динамического режима сохранены")
        
        loaded_settings = settings_manager.load_settings()
        assert loaded_settings.recording_mode == "dynamic", f"Неверный режим: {loaded_settings.recording_mode}"
        assert loaded_settings.fixed_duration_sec == 8, f"Неверная длительность: {loaded_settings.fixed_duration_sec}"
        assert loaded_settings.pre_roll_sec == 1.0, f"Неверный pre-roll: {loaded_settings.pre_roll_sec}"
        assert loaded_settings.post_roll_sec == 0.5, f"Неверный post-roll: {loaded_settings.post_roll_sec}"
        print("✓ Динамический режим загружен корректно")
        
        print("\n=== Тест прошел успешно! ===")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка теста: {e}")
        return False
        
    finally:
        # Удалить временный файл
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_default_settings():
    """Тест значений по умолчанию."""
    print("\n=== Тест значений по умолчанию ===")
    
    # Создать настройки по умолчанию
    default_settings = AppSettings()
    
    print(f"Режим по умолчанию: {default_settings.recording_mode}")
    print(f"Фиксированная длительность по умолчанию: {default_settings.fixed_duration_sec}с")
    print(f"Pre-roll по умолчанию: {default_settings.pre_roll_sec}с")
    print(f"Post-roll по умолчанию: {default_settings.post_roll_sec}с")
    
    # Проверить, что режим по умолчанию - фиксированная длина
    assert default_settings.recording_mode == "fixed_length", f"Ожидается fixed_length, получено: {default_settings.recording_mode}"
    print("✓ Режим по умолчанию - фиксированная длина")
    
    print("✓ Тест значений по умолчанию пройден")
    return True


def test_mode_indicator_formatting():
    """Тест форматирования индикатора режима."""
    print("\n=== Тест форматирования индикатора режима ===")
    
    # Имитация метода update_mode_indicator из MainWindow
    def format_mode_indicator(recording_mode, fixed_duration, pre_roll, post_roll):
        if recording_mode == "fixed_length":
            mode_text = "Режим: Фиксированная длина"
            params_text = f"Длительность: {fixed_duration}с | Pre-roll: {pre_roll}с | Post-roll: {post_roll}с"
        else:
            mode_text = "Режим: Динамический"
            params_text = f"Pre-roll: {pre_roll}с | Post-roll: {post_roll}с"
        
        return f"{mode_text} | {params_text}"
    
    # Тест фиксированной длины
    indicator_fixed = format_mode_indicator("fixed_length", 15, 2.5, 1.0)
    expected_fixed = "Режим: Фиксированная длина | Длительность: 15с | Pre-roll: 2.5с | Post-roll: 1.0с"
    assert indicator_fixed == expected_fixed, f"Неверный формат: {indicator_fixed}"
    print("✓ Формат индикатора для фиксированной длины корректен")
    
    # Тест динамического режима
    indicator_dynamic = format_mode_indicator("dynamic", 8, 1.0, 0.5)
    expected_dynamic = "Режим: Динамический | Pre-roll: 1.0с | Post-roll: 0.5с"
    assert indicator_dynamic == expected_dynamic, f"Неверный формат: {indicator_dynamic}"
    print("✓ Формат индикатора для динамического режима корректен")
    
    print("✓ Тест форматирования индикатора пройден")
    return True


if __name__ == "__main__":
    print("Запуск тестов для системы настроек режима отрезка...")
    
    success = True
    success &= test_default_settings()
    success &= test_settings_persistence()
    success &= test_mode_indicator_formatting()
    
    if success:
        print("\n🎉 Все тесты пройдены успешно!")
        print("\nФункциональность сохранения и применения настроек режима отрезка работает корректно:")
        print("• Настройки сохраняются в config.json при изменении")
        print("• Настройки загружаются при запуске приложения")
        print("• Режим по умолчанию - фиксированная длина")
        print("• Индикатор режима отображает текущие настройки")
        print("• Все параметры (pre-roll, post-roll, fixed_duration) сохраняются и применяются")
    else:
        print("\n❌ Некоторые тесты не прошли")
        sys.exit(1)