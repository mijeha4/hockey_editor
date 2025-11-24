#!/usr/bin/env python3
"""
Hockey Editor - Профессиональный видеомонтажер для анализа хоккейных матчей.
Запуск: python main.py
"""

import sys
import os

# Добавить корневую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# Импорты компонентов
from core.video_controller import VideoController
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    
    # Создать контроллер видео
    controller = VideoController()
    
    # Создать главное окно
    window = MainWindow(controller)
    controller.set_view(window)
    
    # Показать окно
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


