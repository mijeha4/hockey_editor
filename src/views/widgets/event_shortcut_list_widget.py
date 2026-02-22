"""
Event Shortcut List Widget - displays events and shortcuts, allows rebinding.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, Signal, QPropertyAnimation
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QLabel, QMessageBox, QInputDialog, QSizePolicy
)

from services.events.custom_event_manager import get_custom_event_manager
from services.events.custom_event_type import CustomEventType


class EventShortcutListWidget(QWidget):
    event_selected = Signal(str)  # event_name

    def __init__(self, parent=None):
        super().__init__(parent)

        self.event_manager = get_custom_event_manager()
        self.is_collapsed = False
        self.animation = None

        self._setup_ui()
        self.event_manager.events_changed.connect(self.update_event_list)
        self.update_event_list()

    def _setup_ui(self) -> None:
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel("Горячие клавиши событий")
        self.title_label.setStyleSheet("""
            QLabel { color: #ffffff; font-weight: bold; font-size: 11px; }
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
            QPushButton:hover { background-color: #555555; }
        """)
        self.toggle_button.clicked.connect(self.toggle_panel)
        header_layout.addWidget(self.toggle_button)

        main_layout.addLayout(header_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setMaximumHeight(300)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
        """)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        self.event_list = QListWidget()
        self.event_list.setStyleSheet("""
            QListWidget {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                selection-background-color: #444444;
            }
            QListWidget::item { padding: 4px; border-bottom: 1px solid #333333; }
            QListWidget::item:hover { background-color: #333333; }
            QListWidget::item:selected { background-color: #444444; }
        """)

        self.event_list.itemClicked.connect(self._on_event_clicked)
        self.event_list.itemDoubleClicked.connect(self._on_event_double_clicked)

        layout.addWidget(self.event_list)
        self.scroll_area.setWidget(container)
        main_layout.addWidget(self.scroll_area)

    def update_event_list(self) -> None:
        self.event_list.clear()

        for event in self.event_manager.get_all_events():
            localized = event.get_localized_name()
            shortcut = (event.shortcut or "").upper()
            text = f"{localized} [{shortcut}]" if shortcut else f"{localized} [Нет клавиши]"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, event.name)

            pixmap = QPixmap(16, 16)
            pixmap.fill(event.get_qcolor())
            item.setIcon(QIcon(pixmap))

            desc = event.get_localized_description() or ""
            tooltip = localized
            if desc:
                tooltip += f"\n{desc}"
            tooltip += f"\nКлавиша: {shortcut}" if shortcut else "\nНет назначенной клавиши"
            item.setToolTip(tooltip)

            self.event_list.addItem(item)

        self._update_visibility()

    def toggle_panel(self) -> None:
        self.is_collapsed = not self.is_collapsed

        self.animation = QPropertyAnimation(self.scroll_area, b"maximumHeight")
        self.animation.setDuration(200)

        if self.is_collapsed:
            self.animation.setStartValue(self.scroll_area.maximumHeight())
            self.animation.setEndValue(0)
            self.toggle_button.setText("▶")
        else:
            self.animation.setStartValue(0)
            self.animation.setEndValue(300)
            self.toggle_button.setText("▼")

        self.animation.start()

    def _update_visibility(self) -> None:
        self.scroll_area.setMaximumHeight(0 if self.is_collapsed else 300)
        self.toggle_button.setText("▶" if self.is_collapsed else "▼")

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
            f"Введите новую клавишу для события '{localized}':",
            text=current_shortcut,
        )
        if not ok:
            return

        new_shortcut = (new_shortcut or "").strip().upper()

        # remove shortcut
        if not new_shortcut:
            updated = replace(event, shortcut="")
            if self.event_manager.update_event(event_name, updated):
                QMessageBox.information(self, "Успех", f"Горячая клавиша удалена для '{localized}'")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить горячую клавишу")
            return

        # check availability (public API)
        if not self.event_manager.is_shortcut_available(new_shortcut, exclude_event=event_name):
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
                    f"Клавиша '{new_shortcut}' уже используется '{conf_loc}'.\n\n"
                    f"Переназначить её на '{localized}'?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    # clear conflicting shortcut
                    cleared_conf = replace(conflicting, shortcut="")
                    self.event_manager.update_event(conflicting.name, cleared_conf)

                    updated = replace(event, shortcut=new_shortcut)
                    if self.event_manager.update_event(event_name, updated):
                        QMessageBox.information(
                            self, "Успех",
                            f"Клавиша '{new_shortcut}' переназначена от '{conf_loc}' к '{localized}'"
                        )
                    else:
                        QMessageBox.warning(self, "Ошибка", "Не удалось переназначить горячую клавишу")
            else:
                QMessageBox.warning(self, "Конфликт", f"Клавиша '{new_shortcut}' недоступна")
            return

        # assign normally
        updated = replace(event, shortcut=new_shortcut)
        if self.event_manager.update_event(event_name, updated):
            QMessageBox.information(self, "Успех", f"Клавиша '{new_shortcut}' назначена для '{localized}'")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось назначить горячую клавишу")

    def get_preferred_height(self) -> int:
        if self.is_collapsed:
            return 25
        event_count = len(self.event_manager.get_all_events())
        item_height = 24
        header_height = 25
        max_height = 300
        return header_height + min(event_count * item_height, max_height)