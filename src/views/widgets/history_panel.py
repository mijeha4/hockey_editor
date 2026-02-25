# src/views/widgets/history_panel.py
"""
Панель истории Undo/Redo — стек команд с возможностью навигации кликом.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QFrame,
)
from PySide6.QtGui import QColor

from services.history.history_manager import HistoryManager, get_history_manager


class HistoryPanel(QWidget):
    """
    Виджет панели истории.

    Показывает:
     - Кнопки Undo / Redo / Clear
     - Стек команд: undo-часть яркая, redo-часть полупрозрачная
     - Счётчик команд
     - Клик по элементу = undo/redo до этой позиции
    """

    def __init__(
        self,
        history_manager: Optional[HistoryManager] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._history = history_manager or get_history_manager()
        self._setup_ui()
        self._connect_signals()
        self._refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # ── Header ──
        header = QHBoxLayout()
        header.setSpacing(4)

        title = QLabel("📜 История")
        title.setStyleSheet(
            "color: #ffffff; font-weight: bold; font-size: 12px;"
        )
        header.addWidget(title)
        header.addStretch()

        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color: #888888; font-size: 10px;")
        header.addWidget(self._count_label)

        layout.addLayout(header)

        # ── Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        self._undo_btn = QPushButton("↩ Отменить")
        self._undo_btn.setToolTip("Отменить (Ctrl+Z)")
        self._undo_btn.clicked.connect(self._on_undo)
        self._style_button(self._undo_btn)
        btn_layout.addWidget(self._undo_btn)

        self._redo_btn = QPushButton("↪ Повторить")
        self._redo_btn.setToolTip("Повторить (Ctrl+Y)")
        self._redo_btn.clicked.connect(self._on_redo)
        self._style_button(self._redo_btn)
        btn_layout.addWidget(self._redo_btn)

        self._clear_btn = QPushButton("🗑")
        self._clear_btn.setFixedWidth(32)
        self._clear_btn.setToolTip("Очистить историю")
        self._clear_btn.clicked.connect(self._on_clear)
        self._style_button(self._clear_btn)
        btn_layout.addWidget(self._clear_btn)

        layout.addLayout(btn_layout)

        # ── Separator ──
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #444444;")
        layout.addWidget(line)

        # ── Command list ──
        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 4px;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 3px 6px;
                border-bottom: 1px solid #2a2a2a;
            }
            QListWidget::item:selected {
                background-color: #0d47a1;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #333333;
            }
        """)
        self._list.setMaximumHeight(200)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list, 1)

    def _style_button(self, btn: QPushButton) -> None:
        btn.setFixedHeight(26)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #2a2a2a;
                color: #cccccc;
                border: 1px solid #444444;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                color: #ffffff;
                border-color: #666666;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
            QPushButton:disabled {
                background-color: #1e1e1e;
                color: #555555;
                border-color: #333333;
            }
        """)

    def _connect_signals(self) -> None:
        self._history.state_changed.connect(self._refresh)

    def _refresh(self) -> None:
        """Перестроить список и обновить кнопки."""
        self._undo_btn.setEnabled(self._history.can_undo)
        self._redo_btn.setEnabled(self._history.can_redo)
        self._clear_btn.setEnabled(
            self._history.can_undo or self._history.can_redo
        )

        # Tooltips
        if self._history.can_undo:
            self._undo_btn.setToolTip(
                f"Отменить: {self._history.undo_text} (Ctrl+Z)"
            )
        else:
            self._undo_btn.setToolTip("Нечего отменять")

        if self._history.can_redo:
            self._redo_btn.setToolTip(
                f"Повторить: {self._history.redo_text} (Ctrl+Y)"
            )
        else:
            self._redo_btn.setToolTip("Нечего повторять")

        # Counter
        total = self._history.history_count + len(self._history.redo_history)
        self._count_label.setText(f"{total} команд" if total else "")

        # ── Rebuild list ──
        self._list.blockSignals(True)
        self._list.clear()

        # Redo items (сверху, тусклые)
        redo_names = list(reversed(self._history.redo_history))
        for name in redo_names:
            item = QListWidgetItem(f"  ↪ {name}")
            item.setForeground(QColor("#666666"))
            item.setData(Qt.ItemDataRole.UserRole, "redo")
            self._list.addItem(item)

        # Separator: текущая позиция
        if self._history.can_undo or self._history.can_redo:
            sep_item = QListWidgetItem("── текущее состояние ──")
            sep_item.setForeground(QColor("#00cc88"))
            sep_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._list.addItem(sep_item)

        # Undo items (снизу, яркие)
        undo_names = self._history.undo_history  # от новых к старым
        for name in undo_names:
            item = QListWidgetItem(f"  ↩ {name}")
            item.setForeground(QColor("#cccccc"))
            item.setData(Qt.ItemDataRole.UserRole, "undo")
            self._list.addItem(item)

        self._list.blockSignals(False)

    def _on_undo(self) -> None:
        self._history.undo()

    def _on_redo(self) -> None:
        self._history.redo()

    def _on_clear(self) -> None:
        self._history.clear()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """Клик по элементу — множественный undo/redo до этой позиции."""
        role = item.data(Qt.ItemDataRole.UserRole)
        if role is None:
            return

        row = self._list.row(item)
        redo_count = len(self._history.redo_history)

        if role == "redo":
            steps = redo_count - row
            for _ in range(steps):
                if not self._history.can_redo:
                    break
                self._history.redo()

        elif role == "undo":
            undo_row = row - redo_count - 1  # -1 за separator
            steps = undo_row + 1
            for _ in range(steps):
                if not self._history.can_undo:
                    break
                self._history.undo()