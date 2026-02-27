"""
Event Shortcut List Widget — список событий с горячими клавишами.
Отображается как вкладка в правой панели.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QMessageBox, QInputDialog, QSizePolicy
)

from services.events.custom_event_manager import get_custom_event_manager
from services.events.custom_event_type import CustomEventType


class EventShortcutListWidget(QWidget):
    """Список событий с горячими клавишами.

    Клик — отправить событие (эмулировать нажатие горячей клавиши).
    Двойной клик — переназначить горячую клавишу.
    """

    event_selected = Signal(str)  # event_name

    def __init__(self, parent=None):
        super().__init__(parent)

        self.event_manager = get_custom_event_manager()

        self._setup_ui()
        self.event_manager.events_changed.connect(self.update_event_list)
        self.update_event_list()

    def _setup_ui(self) -> None:
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # ── Подсказка ──
        hint = QLabel("Клик — отметить событие  •  Двойной клик — сменить клавишу")
        hint.setStyleSheet("color: #666666; font-size: 9px; padding: 2px 4px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # ── Список событий ──
        self.event_list = QListWidget()
        self.event_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #333333;
                border-radius: 4px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #2a2a2a;
            }
            QListWidget::item:hover {
                background-color: #333333;
            }
            QListWidget::item:selected {
                background-color: #0d47a1;
                color: white;
            }
        """)

        self.event_list.itemClicked.connect(self._on_event_clicked)
        self.event_list.itemDoubleClicked.connect(self._on_event_double_clicked)

        layout.addWidget(self.event_list, 1)

    def update_event_list(self) -> None:
        """Перестроить список событий."""
        self.event_list.clear()

        for event in self.event_manager.get_all_events():
            localized = event.get_localized_name()
            shortcut = (event.shortcut or "").upper()

            if shortcut:
                text = f"  [{shortcut}]  {localized}"
            else:
                text = f"  [—]  {localized}"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, event.name)

            # Цветная иконка
            pixmap = QPixmap(14, 14)
            pixmap.fill(event.get_qcolor())
            item.setIcon(QIcon(pixmap))

            # Tooltip
            desc = event.get_localized_description() or ""
            tooltip = localized
            if desc:
                tooltip += f"\n{desc}"
            if shortcut:
                tooltip += f"\nКлавиша: {shortcut}"
            else:
                tooltip += "\nНет назначенной клавиши"
            tooltip += "\n\nКлик — отметить событие\nДвойной клик — сменить клавишу"
            item.setToolTip(tooltip)

            self.event_list.addItem(item)

    def _on_event_clicked(self, item: QListWidgetItem) -> None:
        event_name = item.data(Qt.UserRole)
        if event_name:
            self.event_selected.emit(event_name)

    def _on_event_double_clicked(self, item: QListWidgetItem) -> None:
        event_name = item.data(Qt.UserRole)
        if not event_name:
            return

        event = self.event_manager.get_event(event_name)
        if not event:
            return

        current_shortcut = event.shortcut or ""
        localized = event.get_localized_name()

        new_shortcut, ok = QInputDialog.getText(
            self,
            "Редактировать горячую клавишу",
            f"Введите новую клавишу для события «{localized}»:\n\n"
            f"(оставьте пустым чтобы удалить)",
            text=current_shortcut,
        )
        if not ok:
            return

        new_shortcut = (new_shortcut or "").strip().upper()

        # Удалить привязку
        if not new_shortcut:
            updated = replace(event, shortcut="")
            if self.event_manager.update_event(event_name, updated):
                QMessageBox.information(
                    self, "Успех",
                    f"Горячая клавиша удалена для «{localized}»"
                )
            else:
                QMessageBox.warning(
                    self, "Ошибка",
                    "Не удалось удалить горячую клавишу"
                )
            return

        # Проверить доступность
        if not self.event_manager.is_shortcut_available(
            new_shortcut, exclude_event=event_name
        ):
            conflicting = None
            for e in self.event_manager.get_all_events():
                if e.name != event_name and (e.shortcut or "").upper() == new_shortcut:
                    conflicting = e
                    break

            if conflicting:
                conf_loc = conflicting.get_localized_name()
                reply = QMessageBox.question(
                    self,
                    "Конфликт горячих клавиш",
                    f"Клавиша «{new_shortcut}» уже используется «{conf_loc}».\n\n"
                    f"Переназначить её на «{localized}»?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    cleared_conf = replace(conflicting, shortcut="")
                    self.event_manager.update_event(conflicting.name, cleared_conf)

                    updated = replace(event, shortcut=new_shortcut)
                    if self.event_manager.update_event(event_name, updated):
                        QMessageBox.information(
                            self, "Успех",
                            f"Клавиша «{new_shortcut}» переназначена "
                            f"от «{conf_loc}» к «{localized}»"
                        )
                    else:
                        QMessageBox.warning(
                            self, "Ошибка",
                            "Не удалось переназначить горячую клавишу"
                        )
            else:
                QMessageBox.warning(
                    self, "Конфликт",
                    f"Клавиша «{new_shortcut}» недоступна"
                )
            return

        # Назначить
        updated = replace(event, shortcut=new_shortcut)
        if self.event_manager.update_event(event_name, updated):
            QMessageBox.information(
                self, "Успех",
                f"Клавиша «{new_shortcut}» назначена для «{localized}»"
            )
        else:
            QMessageBox.warning(
                self, "Ошибка",
                "Не удалось назначить горячую клавишу"
            )