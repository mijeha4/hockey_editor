#!/usr/bin/env python3
"""
Hockey Editor - MVC Architecture
Main entry point
"""

import sys
import os

# Добавить src в путь для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from controllers.main_controller import MainController


def main():
    """Запуск приложения."""
    app = QApplication(sys.argv)
    app.setApplicationName("Hockey Editor")
    app.setApplicationVersion("1.0.0")

    # Создать главный контроллер (он создаст все компоненты)
    controller = MainController()

    # Запустить приложение
    controller.run()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
