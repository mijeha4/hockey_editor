#!/usr/bin/env python3
"""
Тест для проверки функционала клика по таймлайну.
"""

import sys
import os

# Добавляем src в путь для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from controllers.main_controller import MainController

def test_timeline_seek():
    """Тест клика по таймлайну."""
    app = QApplication(sys.argv)

    # Создаем контроллер
    controller = MainController()

    # Настраиваем timeline без видео
    controller.timeline_controller.set_total_frames(1000)
    controller.timeline_controller.set_fps(30.0)

    print("Тестируем клик по таймлайну без видео...")

    # Имитируем клик по таймлайну на кадре 100
    controller.timeline_controller.seek_frame(100)
    print(f"Текущий кадр timeline_controller: {controller.timeline_controller.get_current_frame_idx()}")
    print(f"Текущий кадр playback_controller: {controller.playback_controller.current_frame}")

    # Проверяем, что кадры синхронизированы
    assert controller.timeline_controller.get_current_frame_idx() == controller.playback_controller.current_frame == 100
    print("✓ Клик по таймлайну работает корректно")

    # Тестируем обратную синхронизацию (из playback в timeline)
    controller.playback_controller.seek_to_frame(200)
    print(f"После seek_to_frame(200):")
    print(f"Текущий кадр timeline_controller: {controller.timeline_controller.get_current_frame_idx()}")
    print(f"Текущий кадр playback_controller: {controller.playback_controller.current_frame}")

    # Проверяем синхронизацию
    assert controller.timeline_controller.get_current_frame_idx() == controller.playback_controller.current_frame == 200
    print("✓ Синхронизация из playback в timeline работает корректно")

    print("✓ Все тесты пройдены успешно!")

if __name__ == "__main__":
    test_timeline_seek()
