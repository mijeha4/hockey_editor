"""
New Project Dialog - Modern modal dialog for project creation mode selection.

Features:
- Sleek modern modal dialog with glassmorphism effects
- Teal accent colors and clean typography
- Dark & light mode support
- Professional desktop app styling
- Rounded corners and blur effects
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QRadioButton,
    QPushButton, QButtonGroup, QDialogButtonBox, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette
from src.models.config.app_settings import Theme
from src.services.serialization.settings_manager import SettingsManager


class NewProjectDialog(QDialog):
    """Modern modal dialog for project creation mode selection."""

    # Режимы создания проекта
    MODE_CURRENT_WINDOW = "current"
    MODE_NEW_WINDOW = "new"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание нового проекта")
        self.setModal(True)
        self.selected_mode = self.MODE_CURRENT_WINDOW

        # Standard window frame for professional look
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self._setup_ui()
        self._apply_theme()
        self._apply_professional_styling()

    def _setup_ui(self):
        """Настройка профессионального интерфейса как в DaVinci Resolve."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title bar
        title_label = QLabel("Создание нового проекта")
        title_label.setObjectName("dialogTitle")
        main_layout.addWidget(title_label)

        # Content container
        content_widget = QWidget()
        content_widget.setObjectName("dialogContainer")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(0)

        # Subtitle
        subtitle_label = QLabel("Выберите режим создания проекта")
        subtitle_label.setObjectName("dialogSubtitle")
        content_layout.addWidget(subtitle_label)

        # Radio button container
        radio_container = QWidget()
        radio_container.setObjectName("radioContainer")
        radio_layout = QVBoxLayout(radio_container)
        radio_layout.setContentsMargins(20, 20, 20, 20)
        radio_layout.setSpacing(12)

        # Группа радиокнопок
        self.button_group = QButtonGroup(self)

        # Вариант 1: Текущее окно
        self.current_window_radio = QRadioButton("Создать в текущем окне")
        self.current_window_radio.setObjectName("modernRadio")
        self.current_window_radio.setChecked(True)
        self.current_window_radio.setToolTip("Заменит текущий проект новым")
        self.button_group.addButton(self.current_window_radio, 0)
        radio_layout.addWidget(self.current_window_radio)

        # Description for current window option
        current_desc = QLabel("Текущий проект будет заменён новым")
        current_desc.setObjectName("radioDescription")
        radio_layout.addWidget(current_desc)

        # Spacing
        radio_layout.addSpacing(8)

        # Вариант 2: Новое окно
        self.new_window_radio = QRadioButton("Создать в новом окне")
        self.new_window_radio.setObjectName("modernRadio")
        self.new_window_radio.setToolTip("Откроет новый экземпляр приложения")
        self.button_group.addButton(self.new_window_radio, 1)
        radio_layout.addWidget(self.new_window_radio)

        # Description for new window option
        new_desc = QLabel("Будет открыт новый экземпляр приложения")
        new_desc.setObjectName("radioDescription")
        radio_layout.addWidget(new_desc)

        content_layout.addWidget(radio_container)

        # Add content widget to main layout
        main_layout.addWidget(content_widget)

        # Bottom action bar
        button_container = QWidget()
        button_container.setObjectName("buttonContainer")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(20, 0, 20, 0)
        button_layout.setSpacing(8)

        # Cancel button (left aligned)
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setObjectName("modernCancelButton")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        # Spacer to push OK button to the right
        button_layout.addStretch()

        # OK button (right aligned)
        self.ok_button = QPushButton("Создать проект")
        self.ok_button.setObjectName("modernOkButton")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)

        main_layout.addWidget(button_container)

        # Подключение сигналов
        self.button_group.buttonClicked.connect(self._on_mode_selected)

        # Настройка размера - достаточный для всего содержимого с запасом
        self.setFixedSize(450, 380)

    def _apply_theme(self):
        """Apply theme-specific styling based on user settings."""
        try:
            settings_manager = SettingsManager()
            current_theme = settings_manager.get_settings().theme

            if current_theme == Theme.DARK.value:
                self.setProperty("class", "dark-mode")
            else:
                self.setProperty("class", "light-mode")
        except Exception as e:
            # Fallback to light mode if settings can't be loaded
            print(f"Warning: Could not load theme settings: {e}")
            self.setProperty("class", "light-mode")

        # Force style refresh
        self.style().unpolish(self)
        self.style().polish(self)

    def _apply_professional_styling(self):
        """Apply professional flat dark theme styling like DaVinci Resolve."""
        self.setStyleSheet("""
            /* Main dialog - dark background matching main window */
            QDialog {
                background-color: #1E1E1E;
                color: #FFFFFF;
            }

            /* Title bar styling */
            #dialogTitle {
                background-color: #2D2D2D;
                color: #FFFFFF;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 16px;
                font-weight: bold;
                padding: 12px 20px;
                margin: 0;
                border-bottom: 1px solid #404040;
            }

            /* Content area with subtle border */
            #dialogContainer {
                background-color: #1E1E1E;
                border: 1px solid #3A3A3A;
                border-radius: 10px;
                padding: 20px;
            }

            /* Subtitle text */
            #dialogSubtitle {
                color: #D4D4D4;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 15px;
                font-weight: normal;
                padding: 10px 0 20px 0;
                margin: 0;
                text-align: center;
            }

            /* Radio container */
            #radioContainer {
                background-color: #252526;
                border: 1px solid #3A3A3A;
                border-radius: 8px;
                padding: 20px;
                margin: 0;
            }

            /* Radio buttons - flat style */
            #modernRadio {
                color: #FFFFFF;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 14px;
                font-weight: normal;
                spacing: 10px;
                padding: 8px;
                background-color: transparent;
                border-radius: 4px;
            }

            #modernRadio::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #606060;
                border-radius: 9px;
                background-color: #252526;
            }

            #modernRadio::indicator:checked {
                background-color: #00C4B4;
                border: 2px solid #00C4B4;
            }

            #modernRadio:hover {
                background-color: #2A2A2A;
            }

            /* Radio descriptions */
            #radioDescription {
                color: #AAAAAA;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 12px;
                padding: 0 0 0 28px;
                margin: 0;
            }

            /* Bottom action bar */
            #buttonContainer {
                background-color: #252526;
                border-top: 1px solid #333333;
                padding: 16px 20px;
                margin: 20px -20px -20px -20px;
            }

            /* Buttons */
            #modernCancelButton, #modernOkButton {
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 13px;
                font-weight: normal;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 100px;
                border: none;
            }

            #modernCancelButton {
                background-color: #3C3C3C;
                color: #FFFFFF;
            }

            #modernCancelButton:hover {
                background-color: #4A4A4A;
            }

            #modernOkButton {
                background-color: #00C4B4;
                color: #FFFFFF;
                font-weight: bold;
            }

            #modernOkButton:hover {
                background-color: #00E0CC;
            }
        """)



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
