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
from hockey_editor.utils.style_manager import get_style_manager


def main():
    """Запуск приложения."""
    app = QApplication(sys.argv)
    app.setApplicationName("Hockey Editor Pro")
    app.setApplicationVersion("2.0.0")

    # Initialize global design system
    style_manager = get_style_manager()
    style_manager.apply_global_styles()

    # Создать контроллер
    controller = VideoController()

    # Создать главное окно
    window = MainWindow(controller)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
