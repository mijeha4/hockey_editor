#!/usr/bin/env python3
"""
Hockey Editor - MVC Architecture
Main entry point
"""

import sys
import os

# Добавить src и hockey_editor в путь для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'hockey_editor'))

from PySide6.QtWidgets import QApplication
from controllers.main_controller import MainController
from controllers.application_controller import initialize_application_controller


def main():
    """Запуск приложения."""
    app = QApplication(sys.argv)
    app.setApplicationName("Hockey Editor")
    app.setApplicationVersion("1.0.0")

    # Инициализировать ApplicationController для управления окнами
    initialize_application_controller(app)

    # Создать главный контроллер (он создаст все компоненты)
    controller = MainController()

    # Запустить приложение
    controller.run()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
