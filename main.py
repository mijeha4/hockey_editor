#!/usr/bin/env python3
"""
Hockey Editor Pro — главная точка входа.
"""

import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Пути импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'hockey_editor'))


def _find_icon_path() -> str:
    """Найти файл иконки приложения."""
    base = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base, 'assets', 'icons', 'app_icon.png'),
        os.path.join(base, 'assets', 'icons', 'app_icon.ico'),
        os.path.join(base, 'assets', 'icons', 'app_icon_256.png'),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return ""


def main():
    """Запуск приложения с загрузочным экраном."""
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon

    app = QApplication(sys.argv)
    app.setApplicationName("Hockey Editor Pro")
    app.setApplicationVersion("1.0.0")

    # ── Иконка приложения ──
    icon_path = _find_icon_path()
    if icon_path:
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    # ── Splash Screen ──
    from views.splash_screen import SplashScreen

    splash = SplashScreen()
    splash.set_version(app.applicationVersion())
    splash.show()
    app.processEvents()

    # ── Шаг 1: Application Controller ──
    splash.set_progress(0.10, "Инициализация приложения...")
    from controllers.application_controller import initialize_application_controller
    initialize_application_controller(app)

    # ── Шаг 2: Настройки ──
    splash.set_progress(0.25, "Загрузка настроек...")
    # (настройки грузятся внутри MainController, но подготовим менеджеры)
    from services.serialization.settings_manager import get_settings_manager
    get_settings_manager()

    # ── Шаг 3: Менеджер событий ──
    splash.set_progress(0.40, "Загрузка типов событий...")
    from services.events.custom_event_manager import get_custom_event_manager
    get_custom_event_manager()

    # ── Шаг 4: История ──
    splash.set_progress(0.50, "Инициализация системы истории...")
    from services.history.history_manager import get_history_manager
    get_history_manager()

    # ── Шаг 5: Видеодвижок ──
    splash.set_progress(0.60, "Инициализация видео-движка...")
    import cv2  # noqa: F401 — проверяем доступность

    # ── Шаг 6: Главный контроллер ──
    splash.set_progress(0.75, "Подготовка интерфейса...")
    from controllers.main_controller import MainController
    controller = MainController()
    app.main_controller = controller

    # ── Шаг 7: Показать окно ──
    splash.set_progress(0.90, "Запуск...")
    controller.run()

    # ── Готово ──
    splash.finish_and_close(delay_ms=500)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()