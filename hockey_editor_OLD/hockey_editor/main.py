#!/usr/bin/env python3
"""
Hockey Editor - Профессиональный видеомонтажер для анализа хоккейных матчей.
Запуск: python -m hockey_editor.main
"""

import sys
import os

# Добавить корневую директорию в Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

# Импорты компонентов
from hockey_editor.core.video_controller import VideoController
from hockey_editor.ui.main_window import MainWindow
from hockey_editor.utils.style_manager import get_style_manager


def main():
    app = QApplication(sys.argv)

    # Initialize global design system
    style_manager = get_style_manager()
    style_manager.apply_global_styles()

    # Проверить наличие файлов восстановления
    from hockey_editor.utils.autosave import AutosaveManager
    recovery_path = AutosaveManager.check_recovery()
    
    # Создать контроллер видео
    controller = VideoController()
    
    # Создать главное окно
    window = MainWindow(controller)
    
    # Показать окно
    window.show()
    
    # Предложить восстановление если есть файл
    if recovery_path:
        reply = QMessageBox.question(
            window, "Recovery",
            f"Previous session crashed. Recover project?\n\n{recovery_path}",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Yes:
            if controller.load_project(recovery_path):
                QMessageBox.information(window, "Success", "Project recovered")
            else:
                QMessageBox.critical(window, "Error", "Failed to recover project")
        elif reply == QMessageBox.No:
            AutosaveManager.clear_recovery()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
