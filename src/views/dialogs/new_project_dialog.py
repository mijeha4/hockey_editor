"""
New Project Dialog - Диалог выбора режима создания нового проекта.

Позволяет пользователю выбрать:
- Создать проект в текущем окне
- Создать проект в новом окне
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton,
    QPushButton, QButtonGroup, QDialogButtonBox
)
from PySide6.QtCore import Qt


class NewProjectDialog(QDialog):
    """Диалог выбора режима создания нового проекта."""

    # Режимы создания проекта
    MODE_CURRENT_WINDOW = "current"
    MODE_NEW_WINDOW = "new"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание нового проекта")
        self.setModal(True)
        self.selected_mode = self.MODE_CURRENT_WINDOW

        self._setup_ui()

    def _setup_ui(self):
        """Настройка пользовательского интерфейса."""
        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel("Выберите режим создания нового проекта:")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title_label)

        # Группа радиокнопок
        self.button_group = QButtonGroup(self)

        # Вариант 1: Текущее окно
        self.current_window_radio = QRadioButton("Создать в текущем окне")
        self.current_window_radio.setChecked(True)
        self.current_window_radio.setToolTip("Заменит текущий проект новым")
        self.button_group.addButton(self.current_window_radio, 0)
        layout.addWidget(self.current_window_radio)

        # Вариант 2: Новое окно
        self.new_window_radio = QRadioButton("Создать в новом окне")
        self.new_window_radio.setToolTip("Откроет новый экземпляр приложения")
        self.button_group.addButton(self.new_window_radio, 1)
        layout.addWidget(self.new_window_radio)

        # Подключение сигналов
        self.button_group.buttonClicked.connect(self._on_mode_selected)

        # Кнопки OK/Cancel
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Настройка размера
        self.setFixedSize(350, 150)

    def _on_mode_selected(self, button):
        """Обработка выбора режима."""
        if button == self.current_window_radio:
            self.selected_mode = self.MODE_CURRENT_WINDOW
        elif button == self.new_window_radio:
            self.selected_mode = self.MODE_NEW_WINDOW

    def get_selected_mode(self) -> str:
        """Возвращает выбранный режим создания проекта."""
        return self.selected_mode

    @staticmethod
    def get_new_project_mode(parent=None) -> str:
        """Статический метод для получения режима создания проекта.

        Returns:
            MODE_CURRENT_WINDOW или MODE_NEW_WINDOW
        """
        dialog = NewProjectDialog(parent)
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            return dialog.get_selected_mode()
        else:
            return None  # Пользователь отменил
