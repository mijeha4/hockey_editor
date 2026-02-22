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

if TYPE_CHECKING:
    from .main_controller import MainController


class ApplicationController(QObject):
    """Контроллер управления приложением и окнами."""

    # Сигналы
    window_closed = Signal()
    last_window_closed = Signal()

    def __init__(self):
        super().__init__()
        self._windows: List["MainController"] = []
        self._app: Optional[QApplication] = None

    def initialize(self, app: QApplication) -> None:
        """Инициализация контроллера с экземпляром QApplication.

        Args:
            app: Экземпляр QApplication.
        """
        self._app = app

    def create_new_window(self) -> "MainController":
        """Создает новое окно приложения.

        Returns:
            MainController: Контроллер нового окна.
        """
        try:
            from .main_controller import MainController
        except ImportError:
            from controllers.main_controller import MainController

        controller = MainController()
        self._windows.append(controller)

        # Подписка на сигнал закрытия окна (MainWindow должен иметь window_closing)
        controller.window_close_requested.connect(
            lambda: self._on_window_close(controller)
        )

        controller.run()
        return controller

    def _on_window_close(self, controller: "MainController") -> None:
        """Обработка закрытия окна.

        Args:
            controller: Контроллер закрываемого окна.
        """
        if controller in self._windows:
            self._windows.remove(controller)

        # Очистка ресурсов контроллера
        controller.cleanup()

        self.window_closed.emit()

        if not self._windows:
            self.last_window_closed.emit()
            if self._app:
                self._app.quit()

    def get_window_count(self) -> int:
        """Возвращает количество открытых окон."""
        return len(self._windows)

    def get_windows(self) -> List["MainController"]:
        """Возвращает копию списка всех контроллеров окон."""
        return self._windows.copy()

    def close_all_windows(self) -> None:
        """Закрывает все окна приложения."""
        for controller in self._windows[:]:
            controller.close()

    def cleanup(self) -> None:
        """Очистка ресурсов контроллера приложения."""
        self.close_all_windows()
        self._app = None


# ─── Глобальный экземпляр ───

_app_controller: Optional[ApplicationController] = None


def get_application_controller() -> ApplicationController:
    """Возвращает глобальный экземпляр ApplicationController."""
    global _app_controller
    if _app_controller is None:
        _app_controller = ApplicationController()
    return _app_controller


def initialize_application_controller(app: QApplication) -> ApplicationController:
    """Инициализирует глобальный ApplicationController.

    Args:
        app: Экземпляр QApplication.

    Returns:
        Инициализированный ApplicationController.
    """
    controller = get_application_controller()
    controller.initialize(app)
    return controller