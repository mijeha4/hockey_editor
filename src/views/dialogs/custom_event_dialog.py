"""
Диалог управления пользовательскими типами событий.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QInputDialog, QColorDialog, QFormLayout,
    QLineEdit, QLabel, QGroupBox
)
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtCore import Qt

# === FIX: убран префикс src. — иначе создаётся второй singleton ===
from services.events.custom_event_manager import CustomEventManager, get_custom_event_manager
from services.events.custom_event_type import CustomEventType


class CustomEventDialog(QDialog):
    """Диалог добавления/редактирования типа события."""

    def __init__(self, parent=None, event: Optional[CustomEventType] = None):
        super().__init__(parent)
        self._event = event
        self.is_edit_mode = event is not None
        self.selected_color = QColor(event.color) if event else QColor('#CCCCCC')

        self.setWindowTitle(
            'Редактировать тип события' if self.is_edit_mode else 'Добавить тип события'
        )
        self.setModal(True)
        self.setMinimumWidth(400)

        self._create_ui()
        self._load_data()

    def _create_ui(self) -> None:
        layout = QVBoxLayout()

        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('например: Power Play, Icing...')
        form.addRow('Название:', self.name_input)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText('например: Игра в большинстве')
        form.addRow('Описание:', self.desc_input)

        self.shortcut_input = QLineEdit()
        self.shortcut_input.setPlaceholderText('например: W, Q, R')
        form.addRow('Горячая клавиша:', self.shortcut_input)

        layout.addLayout(form)

        color_group = QGroupBox('Цвет')
        color_layout = QHBoxLayout()

        self.color_label = QLabel()
        self.color_label.setFixedSize(40, 40)
        self.color_label.setStyleSheet('border: 1px solid #333;')
        self._update_color_label()

        color_btn = QPushButton('Выбрать цвет...')
        color_btn.clicked.connect(self._on_choose_color)

        color_layout.addWidget(self.color_label)
        color_layout.addWidget(color_btn)
        color_layout.addStretch()
        color_group.setLayout(color_layout)

        layout.addWidget(color_group)

        button_layout = QHBoxLayout()

        ok_btn = QPushButton('ОК')
        ok_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _load_data(self) -> None:
        if self.is_edit_mode and self._event:
            self.name_input.setText(self._event.name)
            self.desc_input.setText(self._event.description)
            self.shortcut_input.setText(self._event.shortcut)
            self.selected_color = QColor(self._event.color)
            self._update_color_label()
            self.name_input.setReadOnly(True)

    def _on_choose_color(self) -> None:
        color = QColorDialog.getColor(self.selected_color, self, 'Выберите цвет события')
        if color.isValid():
            self.selected_color = color
            self._update_color_label()

    def _update_color_label(self) -> None:
        self.color_label.setStyleSheet(
            f'background-color: {self.selected_color.name()}; border: 1px solid #333;'
        )

    def get_event(self) -> CustomEventType:
        return CustomEventType(
            name=self.name_input.text().strip(),
            color=self.selected_color.name(),
            shortcut=self.shortcut_input.text().strip(),
            description=self.desc_input.text().strip()
        )


class CustomEventManagerDialog(QDialog):
    """Диалог управления всеми типами событий."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager: CustomEventManager = get_custom_event_manager()

        self.setWindowTitle('Управление типами событий')
        self.setModal(True)
        self.setMinimumSize(500, 400)

        self._create_ui()
        self._refresh_list()

    def _create_ui(self) -> None:
        layout = QVBoxLayout()

        list_label = QLabel('Типы событий:')
        layout.addWidget(list_label)

        self.event_list = QListWidget()
        self.event_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.event_list.itemDoubleClicked.connect(self._on_edit_event)
        layout.addWidget(self.event_list)

        button_layout = QHBoxLayout()

        self.add_btn = QPushButton('➕ Добавить')
        self.add_btn.clicked.connect(self._on_add_event)
        button_layout.addWidget(self.add_btn)

        self.edit_btn = QPushButton('✏️ Редактировать')
        self.edit_btn.clicked.connect(self._on_edit_event)
        self.edit_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn)

        self.delete_btn = QPushButton('🗑️ Удалить')
        self.delete_btn.clicked.connect(self._on_delete_event)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)

        button_layout.addStretch()

        reset_btn = QPushButton('↺ Сбросить по умолчанию')
        reset_btn.clicked.connect(self._on_reset)
        button_layout.addWidget(reset_btn)

        layout.addLayout(button_layout)

        dialog_buttons = QHBoxLayout()
        close_btn = QPushButton('Закрыть')
        close_btn.clicked.connect(self.accept)
        dialog_buttons.addStretch()
        dialog_buttons.addWidget(close_btn)

        layout.addLayout(dialog_buttons)
        self.setLayout(layout)

    def _refresh_list(self) -> None:
        self.event_list.clear()

        for event in self.manager.get_all_events():
            item = QListWidgetItem()

            pixmap = QPixmap(20, 20)
            pixmap.fill(event.get_qcolor())
            icon = QIcon(pixmap)

            localized = event.get_localized_name()
            text = f"{localized}"
            if event.shortcut:
                text += f" [{event.shortcut}]"
            if event.description:
                text += f" — {event.description}"

            # Показать оригинальное имя если отличается
            if localized != event.name:
                text += f"  ({event.name})"

            item.setIcon(icon)
            item.setText(text)
            item.setData(Qt.UserRole, event.name)

            # Пометить стандартные события серым
            is_default = self.manager.is_default_event(event.name)
            if is_default:
                item.setForeground(QColor("#aaaaaa"))

            self.event_list.addItem(item)

    def _on_selection_changed(self) -> None:
        selected = self.event_list.selectedItems()
        has_selection = len(selected) > 0

        self.edit_btn.setEnabled(has_selection)

        if has_selection:
            event_name = selected[0].data(Qt.UserRole)
            event = self.manager.get_event(event_name)
            if event is None:
                self.delete_btn.setEnabled(False)
                return
            is_default = self.manager.is_default_event(event.name)
            self.delete_btn.setEnabled(not is_default)
        else:
            self.delete_btn.setEnabled(False)

    def _on_add_event(self) -> None:
        dialog = CustomEventDialog(self)
        if dialog.exec() == QDialog.Accepted:
            event = dialog.get_event()
            if not event.name:
                QMessageBox.warning(self, 'Ошибка', 'Название события не может быть пустым')
                return

            if not self.manager.add_event(event):
                QMessageBox.warning(
                    self, 'Ошибка',
                    f'Событие "{event.name}" уже существует или имеет некорректный цвет'
                )
                return

            self._refresh_list()
            QMessageBox.information(
                self, 'Успех', f'Событие "{event.name}" добавлено'
            )

    def _on_edit_event(self) -> None:
        selected = self.event_list.selectedItems()
        if not selected:
            return

        event_name = selected[0].data(Qt.UserRole)
        event = self.manager.get_event(event_name)
        if not event:
            return

        dialog = CustomEventDialog(self, event)
        if dialog.exec() == QDialog.Accepted:
            new_event = dialog.get_event()
            if not self.manager.update_event(event_name, new_event):
                QMessageBox.warning(self, 'Ошибка', 'Не удалось обновить событие')
                return

            self._refresh_list()
            QMessageBox.information(self, 'Успех', 'Событие обновлено')

    def _on_delete_event(self) -> None:
        selected = self.event_list.selectedItems()
        if not selected:
            return

        event_name = selected[0].data(Qt.UserRole)
        event = self.manager.get_event(event_name)
        display_name = event.get_localized_name() if event else event_name

        reply = QMessageBox.question(
            self,
            'Подтверждение удаления',
            f'Удалить тип события "{display_name}"?\n\n'
            f'Все маркеры этого типа будут также удалены.\n'
            f'Это действие можно отменить (Ctrl+Z).',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.manager.delete_event(event_name):
                self._refresh_list()
                QMessageBox.information(
                    self, 'Успех', f'Событие "{display_name}" удалено'
                )
            else:
                QMessageBox.warning(
                    self, 'Ошибка',
                    f'Невозможно удалить стандартное событие "{display_name}"'
                )

    def _on_reset(self) -> None:
        reply = QMessageBox.question(
            self,
            'Подтверждение сброса',
            'Сбросить все события к стандартным?\n\n'
            'Все пользовательские события будут удалены.',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.manager.reset_to_defaults()
            self._refresh_list()
            QMessageBox.information(self, 'Успех', 'События сброшены к стандартным')