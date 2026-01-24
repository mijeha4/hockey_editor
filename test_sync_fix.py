#!/usr/bin/env python3
"""
Тест для проверки исправления синхронизации между InstanceEditWindow и основным UI.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Импорты из проекта
from src.models.domain.marker import Marker
from src.controllers.main_controller import MainController


def test_sync_fix():
    """Тестирование синхронизации после сохранения в InstanceEditWindow."""

    # Создаем QApplication если его нет
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # Создаем MainController (он создаст все компоненты)
    controller = MainController()

    # Создаем тестовый маркер
    marker = Marker(
        start_frame=50,
        end_frame=200,
        event_name="Goal",
        note="Test marker"
    )
    controller.project.markers.append(marker)

    # Обновляем UI
    controller.timeline_controller.refresh_view()

    print("✓ Тестовый маркер создан и UI обновлен")
    print(f"Маркер: {marker.start_frame}-{marker.end_frame}, тип: {marker.event_name}")

    # Имитируем открытие редактора отрезка
    # В реальном приложении это делается через main_window.open_segment_editor(0)

    def simulate_edit_and_save():
        """Имитируем редактирование и сохранение маркера."""
        print("\n--- Имитация редактирования маркера ---")

        # Получаем InstanceEditController
        instance_controller = controller.get_instance_edit_controller()

        # Устанавливаем маркер для редактирования
        instance_controller.set_marker(marker)

        # Имитируем изменение IN точки
        print(f"Старый IN: {marker.start_frame}")
        instance_controller.set_in_point()  # Устанавливаем IN в текущую позицию плейхеда
        print(f"Новый IN: {marker.start_frame}")

        # Имитируем изменение OUT точки
        print(f"Старый OUT: {marker.end_frame}")
        instance_controller.set_out_point()  # Устанавливаем OUT в текущую позицию плейхеда
        print(f"Новый OUT: {marker.end_frame}")

        # Имитируем сохранение
        print("Сохранение изменений...")
        instance_controller.save_changes()

        print("✓ Изменения сохранены, UI должен обновиться")

        # Проверяем, что маркер изменился
        print(f"Финальный маркер: {marker.start_frame}-{marker.end_frame}")

        # Завершаем тест через 2 секунды
        QTimer.singleShot(2000, app.quit)

    # Запускаем имитацию через 1 секунду
    QTimer.singleShot(1000, simulate_edit_and_save)

    # Запускаем приложение
    controller.run()

    print("Тест завершен")


if __name__ == "__main__":
    test_sync_fix()