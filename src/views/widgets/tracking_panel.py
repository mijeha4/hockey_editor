"""
Tracking Panel — панель управления трекингом игроков.
"""

from __future__ import annotations

from typing import Optional, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QScrollArea,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QFont

from views.styles import AppColors


class TrackedPlayerCard(QWidget):
    """Карточка отслеживаемого игрока."""

    remove_requested = Signal(int)   # track_id
    reinit_requested = Signal(int)   # track_id
    focus_requested = Signal(int)    # track_id

    def __init__(self, track_id: int, label: str,
                 color: tuple, parent=None):
        super().__init__(parent)
        self.track_id = track_id
        self._label = label
        self._color = QColor(*color)
        self._confidence = 1.0
        self._is_active = True
        self._is_hovered = False

        self.setFixedHeight(48)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def set_confidence(self, conf: float):
        self._confidence = conf
        self.update()

    def set_active(self, active: bool):
        self._is_active = active
        self.update()

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.focus_requested.emit(self.track_id)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        # Background
        bg = QColor(AppColors.BG_HOVER) if self._is_hovered \
            else QColor(AppColors.BG_SURFACE)
        if not self._is_active:
            bg = QColor(AppColors.BG_SECONDARY)

        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(2, 2, w - 4, h - 4, 8, 8)

        # Color dot
        painter.setBrush(self._color if self._is_active
                         else QColor(AppColors.TEXT_MUTED))
        painter.drawEllipse(14, h // 2 - 6, 12, 12)

        # Label
        font = QFont("Segoe UI", 11, QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(AppColors.TEXT) if self._is_active
                       else QColor(AppColors.TEXT_MUTED))
        painter.drawText(34, h // 2 + 5, self._label)

        # Confidence badge
        conf_text = f"{int(self._confidence * 100)}%"
        conf_font = QFont("JetBrains Mono", 9, QFont.Weight.Bold)
        painter.setFont(conf_font)

        if self._confidence > 0.7:
            conf_color = QColor(AppColors.SUCCESS)
        elif self._confidence > 0.4:
            conf_color = QColor(AppColors.WARNING)
        else:
            conf_color = QColor(AppColors.ERROR)

        painter.setPen(conf_color)
        painter.drawText(w - 80, h // 2 + 5, conf_text)

        # Remove button (on hover)
        if self._is_hovered:
            painter.setPen(QColor(AppColors.TEXT_MUTED))
            remove_font = QFont("Segoe UI", 14)
            painter.setFont(remove_font)
            painter.drawText(w - 30, h // 2 + 6, "✕")

        painter.end()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Проверить клик на кнопку удаления
            if event.pos().x() > self.width() - 40:
                self.remove_requested.emit(self.track_id)
                return
        super().mouseReleaseEvent(event)


class TrackingPanel(QWidget):
    """Панель управления трекингом."""

    # Сигналы
    select_player_requested = Signal()
    clear_all_requested = Signal()
    tracker_type_changed = Signal(str)
    show_trajectory_changed = Signal(bool)
    show_labels_changed = Signal(bool)
    tracking_enabled_changed = Signal(bool)
    remove_player_requested = Signal(int)
    reinit_player_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: Dict[int, TrackedPlayerCard] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setFixedHeight(34)
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {AppColors.BG_SECONDARY};
                border-bottom: 1px solid {AppColors.BORDER};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)

        icon = QLabel("🎯")
        icon.setStyleSheet("font-size: 14px; background: transparent;")
        header_layout.addWidget(icon)

        title = QLabel("Трекинг игроков")
        title.setStyleSheet(f"""
            font-weight: 700; font-size: 12px;
            color: {AppColors.TEXT};
            background: transparent;
        """)
        header_layout.addWidget(title)

        self._count_label = QLabel("0")
        self._count_label.setStyleSheet(f"""
            color: {AppColors.ACCENT_LIGHT};
            background-color: {AppColors.ACCENT_GLOW};
            border-radius: 8px;
            padding: 1px 8px;
            font-size: 10px;
            font-weight: 700;
        """)
        self._count_label.setVisible(False)
        header_layout.addWidget(self._count_label)

        header_layout.addStretch()
        layout.addWidget(header)

        # ── Controls ──
        controls = QWidget()
        controls.setStyleSheet(f"background-color: {AppColors.BG_PRIMARY};")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        controls_layout.setSpacing(6)

        # Select button
        self._select_btn = QPushButton("🎯  Выделить игрока")
        self._select_btn.setFixedHeight(36)
        self._select_btn.setCursor(Qt.PointingHandCursor)
        self._select_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {AppColors.ACCENT};
                color: {AppColors.TEXT_ON_ACCENT};
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {AppColors.ACCENT_LIGHT};
            }}
        """)
        self._select_btn.clicked.connect(self.select_player_requested.emit)
        controls_layout.addWidget(self._select_btn)

        # Settings row
        settings_row = QHBoxLayout()
        settings_row.setSpacing(6)

        settings_row.addWidget(QLabel("Алгоритм:"))
        self._algo_combo = QComboBox()
        self._algo_combo.addItems(["CSRT", "KCF", "MOSSE", "MedianFlow"])
        self._algo_combo.setCurrentText("CSRT")
        self._algo_combo.setMaximumWidth(110)
        self._algo_combo.currentTextChanged.connect(
            self.tracker_type_changed.emit
        )
        settings_row.addWidget(self._algo_combo)
        settings_row.addStretch()

        controls_layout.addLayout(settings_row)

        # Checkboxes
        cb_row = QHBoxLayout()
        self._trajectory_cb = QCheckBox("Траектория")
        self._trajectory_cb.setChecked(True)
        self._trajectory_cb.toggled.connect(self.show_trajectory_changed.emit)
        cb_row.addWidget(self._trajectory_cb)

        self._labels_cb = QCheckBox("Метки")
        self._labels_cb.setChecked(True)
        self._labels_cb.toggled.connect(self.show_labels_changed.emit)
        cb_row.addWidget(self._labels_cb)
        cb_row.addStretch()

        controls_layout.addLayout(cb_row)

        layout.addWidget(controls)

        # ── Player cards ──
        self._cards_scroll = QScrollArea()
        self._cards_scroll.setWidgetResizable(True)
        self._cards_scroll.setFrameShape(QFrame.NoFrame)
        self._cards_scroll.setMaximumHeight(300)
        self._cards_scroll.setStyleSheet(
            f"background-color: {AppColors.BG_PRIMARY};"
        )

        self._cards_container = QWidget()
        self._cards_container.setStyleSheet(
            f"background-color: {AppColors.BG_PRIMARY};"
        )
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(8, 4, 8, 4)
        self._cards_layout.setSpacing(4)
        self._cards_layout.addStretch()

        self._cards_scroll.setWidget(self._cards_container)
        layout.addWidget(self._cards_scroll)

        # ── Clear button ──
        self._clear_btn = QPushButton("🗑  Очистить всё")
        self._clear_btn.setFixedHeight(28)
        self._clear_btn.setVisible(False)
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {AppColors.ERROR};
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 6px;
                font-size: 11px;
                margin: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.1);
            }}
        """)
        self._clear_btn.clicked.connect(self.clear_all_requested.emit)
        layout.addWidget(self._clear_btn)

        layout.addStretch()

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def add_player_card(self, track_id: int, label: str,
                        color: tuple):
        """Добавить карточку игрока."""
        card = TrackedPlayerCard(track_id, label, color)
        card.remove_requested.connect(self.remove_player_requested.emit)
        card.reinit_requested.connect(self.reinit_player_requested.emit)

        self._cards[track_id] = card

        # Вставить перед stretch
        count = self._cards_layout.count()
        self._cards_layout.insertWidget(count - 1, card)

        self._update_count()
        self._clear_btn.setVisible(True)

    def remove_player_card(self, track_id: int):
        """Удалить карточку игрока."""
        if track_id in self._cards:
            card = self._cards.pop(track_id)
            card.deleteLater()
            self._update_count()
            if not self._cards:
                self._clear_btn.setVisible(False)

    def update_player_card(self, track_id: int,
                           confidence: float, is_active: bool):
        """Обновить данные карточки."""
        if track_id in self._cards:
            self._cards[track_id].set_confidence(confidence)
            self._cards[track_id].set_active(is_active)

    def clear_all_cards(self):
        """Удалить все карточки."""
        for card in list(self._cards.values()):
            card.deleteLater()
        self._cards.clear()
        self._update_count()
        self._clear_btn.setVisible(False)

    def set_selecting_mode(self, selecting: bool):
        """Обновить UI при входе/выходе из режима выделения."""
        if selecting:
            self._select_btn.setText("❌  Отменить выделение")
            self._select_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {AppColors.ERROR};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: #dc2626;
                }}
            """)
        else:
            self._select_btn.setText("🎯  Выделить игрока")
            self._select_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {AppColors.ACCENT};
                    color: {AppColors.TEXT_ON_ACCENT};
                    border: none;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {AppColors.ACCENT_LIGHT};
                }}
            """)

    def _update_count(self):
        count = len(self._cards)
        if count > 0:
            self._count_label.setText(str(count))
            self._count_label.setVisible(True)
        else:
            self._count_label.setVisible(False)