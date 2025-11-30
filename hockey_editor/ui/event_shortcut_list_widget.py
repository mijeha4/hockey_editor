"""
Event Shortcut List Widget - displays events with their keyboard shortcuts in a list format.

Replaces the compact button grid with a scrollable list showing event names and their bound keys.
Allows inline editing of shortcuts with validation for exclusivity.
"""

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QRect, QSize
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QKeySequence
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QFrame, QLabel, QLineEdit, QMessageBox,
    QInputDialog, QSizePolicy
)
from ..utils.custom_events import get_custom_event_manager


class EventShortcutListWidget(QWidget):
    """Widget for displaying events with their shortcuts in a list format."""

    # Сигнал при нажатии на элемент события
    event_selected = Signal(str)  # event_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.event_manager = get_custom_event_manager()
        self.is_collapsed = False

        self.setup_ui()
        self.connect_signals()
        self.update_event_list()

    def setup_ui(self):
        """Создание UI."""
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        # Заголовок с кнопкой сворачивания
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel("Event Shortcuts")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.toggle_button = QPushButton("▼")
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: #ffffff;
                border: 1px solid #666666;
                border-radius: 3px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)
        self.toggle_button.setToolTip("Hide/Show event shortcuts")
        self.toggle_button.clicked.connect(self.toggle_panel)
        header_layout.addWidget(self.toggle_button)

        main_layout.addLayout(header_layout)

        # Контейнер для списка с прокруткой
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setMaximumHeight(300)  # Увеличенное ограничение высоты
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2a2a2a;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #666666;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #888888;
            }
        """)

        # Виджет-контейнер для списка
        self.list_container = QWidget()
        list_layout = QVBoxLayout(self.list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(1)

        # Список событий
        self.event_list = QListWidget()
        self.event_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                selection-background-color: #444444;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:hover {
                background-color: #333333;
            }
            QListWidget::item:selected {
                background-color: #444444;
            }
        """)
        self.event_list.itemDoubleClicked.connect(self._on_event_double_clicked)
        self.event_list.itemClicked.connect(self._on_event_clicked)

        list_layout.addWidget(self.event_list)
        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area)

    def connect_signals(self):
        """Подключение сигналов."""
        self.event_manager.events_changed.connect(self.update_event_list)

    def update_event_list(self):
        """Обновление списка событий."""
        self.event_list.clear()

        # Получение всех событий
        events = self.event_manager.get_all_events()

        for event in events:
            # Создание элемента списка
            item_text = f"{event.name}"
            if event.shortcut:
                item_text += f" [{event.shortcut.upper()}]"
            else:
                item_text += " [No Key]"

            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, event.name)  # Сохранить имя события

            # Установка цвета фона через иконку (маленький цветной квадратик)
            from PySide6.QtGui import QPixmap, QIcon
            pixmap = QPixmap(16, 16)
            pixmap.fill(event.get_qcolor())
            icon = QIcon(pixmap)
            item.setIcon(icon)

            # Tooltip с описанием
            tooltip = event.name
            if event.description:
                tooltip += f"\n{event.description}"
            if event.shortcut:
                tooltip += f"\nShortcut: {event.shortcut.upper()}"
            else:
                tooltip += "\nNo shortcut assigned"
            item.setToolTip(tooltip)

            self.event_list.addItem(item)

        self.update_visibility()

    def toggle_panel(self):
        """Переключение видимости панели."""
        self.is_collapsed = not self.is_collapsed

        # Анимация
        self.animation = QPropertyAnimation(self.scroll_area, b"maximumHeight")
        if self.is_collapsed:
            self.animation.setStartValue(self.scroll_area.maximumHeight())
            self.animation.setEndValue(0)
            self.toggle_button.setText("▶")
            self.toggle_button.setToolTip("Show event shortcuts")
        else:
            self.animation.setStartValue(0)
            self.animation.setEndValue(300)
            self.toggle_button.setText("▼")
            self.toggle_button.setToolTip("Hide event shortcuts")

        self.animation.setDuration(200)
        self.animation.start()

    def update_visibility(self):
        """Обновление видимости в зависимости от состояния сворачивания."""
        if self.is_collapsed:
            self.scroll_area.setMaximumHeight(0)
            self.toggle_button.setText("▶")
        else:
            self.scroll_area.setMaximumHeight(300)
            self.toggle_button.setText("▼")

    def _on_event_clicked(self, item: QListWidgetItem):
        """Обработка клика на событии."""
        event_name = item.data(Qt.UserRole)
        self.event_selected.emit(event_name)

    def _on_event_double_clicked(self, item: QListWidgetItem):
        """Обработка двойного клика - редактирование shortcut'а."""
        event_name = item.data(Qt.UserRole)
        event = self.event_manager.get_event(event_name)
        if not event:
            return

        # Диалог для ввода нового shortcut'а
        current_shortcut = event.shortcut if event.shortcut else ""
        new_shortcut, ok = QInputDialog.getText(
            self, "Edit Shortcut",
            f"Enter new shortcut for '{event_name}':\n(Leave empty to remove shortcut)",
            text=current_shortcut
        )

        if ok:
            new_shortcut = new_shortcut.strip().upper()

            # Проверка на пустую строку (удаление shortcut'а)
            if not new_shortcut:
                event.shortcut = ""
                if self.event_manager.update_event(event_name, event):
                    QMessageBox.information(self, "Success", f"Shortcut removed from '{event_name}'")
                else:
                    QMessageBox.warning(self, "Error", "Failed to remove shortcut")
                return

            # Проверка доступности shortcut'а
            if not self.event_manager._is_shortcut_available(new_shortcut, exclude_event=event_name):
                # Найти событие, которое использует этот shortcut
                conflicting_event = None
                for e in self.event_manager.get_all_events():
                    if e.name != event_name and e.shortcut.upper() == new_shortcut:
                        conflicting_event = e
                        break

                if conflicting_event:
                    reply = QMessageBox.question(
                        self, "Shortcut Conflict",
                        f"Shortcut '{new_shortcut}' is already used by '{conflicting_event.name}'.\n\n"
                        "Do you want to reassign it to '{event_name}' instead?",
                        QMessageBox.Yes | QMessageBox.No
                    )

                    if reply == QMessageBox.Yes:
                        # Удалить shortcut у конфликтующего события
                        conflicting_event.shortcut = ""
                        self.event_manager.update_event(conflicting_event.name, conflicting_event)

                        # Присвоить shortcut новому событию
                        event.shortcut = new_shortcut
                        if self.event_manager.update_event(event_name, event):
                            QMessageBox.information(self, "Success",
                                f"Shortcut '{new_shortcut}' reassigned from '{conflicting_event.name}' to '{event_name}'")
                        else:
                            QMessageBox.warning(self, "Error", "Failed to reassign shortcut")
                    # Если No - ничего не делаем
                else:
                    QMessageBox.warning(self, "Error", f"Shortcut '{new_shortcut}' is not available")
            else:
                # Shortcut доступен, присваиваем
                event.shortcut = new_shortcut
                if self.event_manager.update_event(event_name, event):
                    QMessageBox.information(self, "Success", f"Shortcut '{new_shortcut}' assigned to '{event_name}'")
                else:
                    QMessageBox.warning(self, "Error", "Failed to assign shortcut")

    def get_preferred_height(self) -> int:
        """Получение предпочтительной высоты виджета."""
        if self.is_collapsed:
            return 25  # Только заголовок
        else:
            # Расчёт на основе количества элементов
            event_count = len(self.event_manager.get_all_events())
            item_height = 24  # Высота одного элемента
            header_height = 25
            max_height = 300
            preferred_height = header_height + min(event_count * item_height, max_height)
            return preferred_height
