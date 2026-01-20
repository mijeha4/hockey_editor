"""
Save Changes Dialog - Диалог сохранения изменений перед созданием нового проекта.

Предупреждает пользователя о несохраненных изменениях и предлагает:
- Сохранить изменения
- Не сохранять изменения
- Отменить создание нового проекта
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt


class SaveChangesDialog(QDialog):
    """Диалог сохранения изменений."""

    # Результаты диалога
    SAVE = "save"
    DONT_SAVE = "dont_save"
    CANCEL = "cancel"

    def __init__(self, project_name: str = "Untitled", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сохранение изменений")
        self.setModal(True)
        self.result = self.CANCEL

        self.project_name = project_name
        self._setup_ui()

    def _setup_ui(self):
        """Настройка пользовательского интерфейса."""
        layout = QVBoxLayout(self)

        # Сообщение
        message = f"Проект '{self.project_name}' имеет несохраненные изменения.\n\n" \
                 "Сохранить изменения перед созданием нового проекта?"

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        # Кнопки
        button_box = QDialogButtonBox()

        # Кнопка "Сохранить"
        save_button = button_box.addButton(
            "Сохранить", QDialogButtonBox.ButtonRole.AcceptRole
        )
        save_button.setDefault(True)

        # Кнопка "Не сохранять"
        dont_save_button = button_box.addButton(
            "Не сохранять", QDialogButtonBox.ButtonRole.ActionRole
        )

        # Кнопка "Отмена"
        cancel_button = button_box.addButton(
            "Отмена", QDialogButtonBox.ButtonRole.RejectRole
        )

        # Подключение сигналов
        save_button.clicked.connect(self._on_save)
        dont_save_button.clicked.connect(self._on_dont_save)
        cancel_button.clicked.connect(self._on_cancel)

        layout.addWidget(button_box)

        # Настройка размера
        self.setFixedSize(400, 120)

    def _on_save(self):
        """Пользователь выбрал 'Сохранить'."""
        self.result = self.SAVE
        self.accept()

    def _on_dont_save(self):
        """Пользователь выбрал 'Не сохранять'."""
        self.result = self.DONT_SAVE
        self.accept()

    def _on_cancel(self):
        """Пользователь выбрал 'Отмена'."""
        self.result = self.CANCEL
        self.reject()

    def get_result(self) -> str:
        """Возвращает результат выбора пользователя."""
        return self.result

    @staticmethod
    def ask_save_changes(project_name: str = "Untitled", parent=None) -> str:
        """Статический метод для запроса сохранения изменений.

        Returns:
            SAVE, DONT_SAVE или CANCEL
        """
        dialog = SaveChangesDialog(project_name, parent)
        dialog.exec()
        return dialog.get_result()
