#!/usr/bin/env python3
"""
Hockey Editor Pro - Professional Video Analysis Tool
Main entry point
"""

import sys
import os

# Добавить hockey_editor в путь
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'hockey_editor'))

from PySide6.QtWidgets import QApplication
from hockey_editor.core.video_controller import VideoController
from hockey_editor.ui.main_window import MainWindow
from hockey_editor.utils.localization_manager import get_localization_manager


def main():
    """Запуск приложения."""
    app = QApplication(sys.argv)
    app.setApplicationName("Hockey Editor Pro")
    app.setApplicationVersion("2.0.0")

    # Инициализировать менеджер локализации (загрузить переводы и настройки)
    localization_manager = get_localization_manager()

    # Создать контроллер
    controller = VideoController()

    # Создать главное окно
    window = MainWindow(controller)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
