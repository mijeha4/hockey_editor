"""
Application Controller - Управление окнами приложения.

Отвечает за:
- Создание новых окон приложения
- Отслеживание количества открытых окон
- Завершение приложения при закрытии последнего окна
"""

from typing import List, Optional, TYPE_CHECKING
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QObject, Signal

# Отложенный импорт для избежания циклической зависимости
if TYPE_CHECKING:
    from .main_controller import MainController


class ApplicationController(QObject):
    """Контроллер управления приложением и окнами."""

    # Сигналы
    window_closed = Signal()  # Окно закрылось
    last_window_closed = Signal()  # Последнее окно закрылось

    def __init__(self):
        super().__init__()
        self.windows: List = []  # Список контроллеров окон
        self.app: Optional[QApplication] = None

    def initialize(self, app: QApplication):
        """Инициализация контроллера с экземпляром QApplication."""
        self.app = app

    def create_new_window(self):
        """Создает новое окно приложения.

        Returns:
            MainController: Контроллер нового окна
        """
        # Отложенный импорт для избежания циклической зависимости
        try:
            from .main_controller import MainController
        except ImportError:
            from controllers.main_controller import MainController

        # Создаем новый MainController (он автоматически создаст MainWindow)
        main_controller = MainController()

        # Добавляем в список окон
        self.windows.append(main_controller)

        # Подключаем сигнал закрытия окна
        main_controller.main_window.closeEvent = lambda event: self._on_window_close(main_controller, event)

        # Показываем окно
        main_controller.run()

        return main_controller

    def _on_window_close(self, controller, event):
        """Обработка закрытия окна."""
        # Удаляем контроллер из списка
        if controller in self.windows:
            self.windows.remove(controller)

        # Сигнализируем о закрытии окна
        self.window_closed.emit()

        # Если это было последнее окно, завершаем приложение
        if not self.windows:
            self.last_window_closed.emit()
            if self.app:
                self.app.quit()

        # Принимаем событие закрытия
        event.accept()

    def get_window_count(self) -> int:
        """Возвращает количество открытых окон."""
        return len(self.windows)

    def get_windows(self) -> List:
        """Возвращает список всех контроллеров окон."""
        return self.windows.copy()

    def close_all_windows(self):
        """Закрывает все окна приложения."""
        for controller in self.windows[:]:  # Копируем список, так как он изменится
            controller.main_window.close()


# Глобальный экземпляр ApplicationController
_app_controller = None

def get_application_controller() -> ApplicationController:
    """Возвращает глобальный экземпляр ApplicationController."""
    global _app_controller
    if _app_controller is None:
        _app_controller = ApplicationController()
    return _app_controller

def initialize_application_controller(app: QApplication):
    """Инициализирует глобальный ApplicationController."""
    controller = get_application_controller()
    controller.initialize(app)
    return controller
