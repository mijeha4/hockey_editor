# src/views/widgets/toast_notification.py
"""
Toast notification system — замена QMessageBox для неблокирующих уведомлений.

Использование:
    from views.widgets.toast_notification import get_toast_manager
    
    toast = get_toast_manager(main_window)
    toast.success("Проект сохранён")
    toast.error("Не удалось загрузить видео")
    toast.warning("Файл повреждён", action_text="Подробнее", action_callback=show_details)
    toast.info("Авто-сохранение выполнено", duration_ms=2000)
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Callable, List, TYPE_CHECKING

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, Property, Signal, QObject
)
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath, QMouseEvent
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QPushButton,
    QGraphicsOpacityEffect, QApplication
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow


# ─── Toast Types ─────────────────────────────────────────────────────────────

class ToastType(Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


_TOAST_STYLES = {
    ToastType.SUCCESS: {
        "bg": "#1b5e20",
        "border": "#4caf50",
        "icon": "✅",
        "text_color": "#e8f5e9",
    },
    ToastType.WARNING: {
        "bg": "#e65100",
        "border": "#ff9800",
        "icon": "⚠️",
        "text_color": "#fff3e0",
    },
    ToastType.ERROR: {
        "bg": "#b71c1c",
        "border": "#f44336",
        "icon": "❌",
        "text_color": "#ffebee",
    },
    ToastType.INFO: {
        "bg": "#0d47a1",
        "border": "#2196f3",
        "icon": "ℹ️",
        "text_color": "#e3f2fd",
    },
}


# ─── Single Toast Widget ────────────────────────────────────────────────────

class ToastWidget(QWidget):
    """Одно toast-уведомление."""

    closed = Signal()
    action_clicked = Signal()

    TOAST_WIDTH = 360
    TOAST_MIN_HEIGHT = 48
    MARGIN_RIGHT = 20
    MARGIN_BOTTOM = 12

    def __init__(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration_ms: int = 3000,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(self.TOAST_WIDTH)

        self._toast_type = toast_type
        self._duration_ms = duration_ms
        self._action_callback = action_callback
        self._opacity_value: float = 0.0

        style = _TOAST_STYLES[toast_type]

        # --- Layout ---
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        # Icon
        icon_label = QLabel(style["icon"])
        icon_label.setFixedWidth(22)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(f"font-size: 14px; background: transparent;")
        layout.addWidget(icon_label)

        # Message
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(
            f"color: {style['text_color']}; font-size: 12px; background: transparent;"
        )
        msg_label.setMinimumHeight(20)
        layout.addWidget(msg_label, 1)

        # Action button (optional)
        if action_text:
            action_btn = QPushButton(action_text)
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            action_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: #ffffff;
                    border: 1px solid {style['border']};
                    border-radius: 3px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: rgba(255,255,255,0.15);
                }}
            """)
            action_btn.clicked.connect(self._on_action)
            layout.addWidget(action_btn)

        # Close "×"
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {style['text_color']};
                border: none;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: #ffffff;
            }}
        """)
        close_btn.clicked.connect(self.fade_out)
        layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)

        self.adjustSize()
        self.setMinimumHeight(self.TOAST_MIN_HEIGHT)

        # Cache style for paintEvent
        self._bg_color = QColor(style["bg"])
        self._border_color = QColor(style["border"])

        # --- Timers ---
        self._auto_close_timer = QTimer(self)
        self._auto_close_timer.setSingleShot(True)
        self._auto_close_timer.timeout.connect(self.fade_out)

        # --- Opacity animation ---
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    # ── Paint ──

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), 8.0, 8.0)

        bg = QColor(self._bg_color)
        bg.setAlpha(230)
        painter.fillPath(path, bg)

        pen = painter.pen()
        pen.setColor(self._border_color)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.end()

    # ── Show / Hide animations ──

    def show_animated(self) -> None:
        self.show()
        self._fade_anim.stop()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setDuration(250)
        self._fade_anim.start()

        if self._duration_ms > 0:
            self._auto_close_timer.start(self._duration_ms)

    def fade_out(self) -> None:
        self._auto_close_timer.stop()
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity_effect.opacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setDuration(300)
        self._fade_anim.finished.connect(self._on_fade_finished)
        self._fade_anim.start()

    def _on_fade_finished(self) -> None:
        self.closed.emit()
        self.deleteLater()

    def _on_action(self) -> None:
        if self._action_callback:
            self._action_callback()
        self.fade_out()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Клик по toast закрывает его (если нет action)
        if not self._action_callback:
            self.fade_out()
        super().mousePressEvent(event)


# ─── Toast Manager (singleton per window) ────────────────────────────────────

class ToastManager(QObject):
    """
    Менеджер toast-уведомлений.
    
    Стекирует уведомления снизу вверх в правом нижнем углу родительского окна.
    """

    MAX_VISIBLE = 5

    def __init__(self, parent_window: QWidget):
        super().__init__(parent_window)
        self._parent_window = parent_window
        self._active_toasts: List[ToastWidget] = []

    # ── Public API ──

    def success(self, message: str, **kwargs) -> ToastWidget:
        return self._show(message, ToastType.SUCCESS, **kwargs)

    def warning(self, message: str, **kwargs) -> ToastWidget:
        return self._show(message, ToastType.WARNING, **kwargs)

    def error(self, message: str, **kwargs) -> ToastWidget:
        return self._show(message, ToastType.ERROR, **kwargs)

    def info(self, message: str, **kwargs) -> ToastWidget:
        return self._show(message, ToastType.INFO, **kwargs)

    def clear_all(self) -> None:
        for toast in list(self._active_toasts):
            toast.fade_out()

    # ── Internal ──

    def _show(
        self,
        message: str,
        toast_type: ToastType,
        duration_ms: int = 3000,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None,
    ) -> ToastWidget:
        # Ограничиваем число видимых
        while len(self._active_toasts) >= self.MAX_VISIBLE:
            oldest = self._active_toasts[0]
            oldest.fade_out()

        toast = ToastWidget(
            message=message,
            toast_type=toast_type,
            duration_ms=duration_ms,
            action_text=action_text,
            action_callback=action_callback,
            parent=self._parent_window,
        )
        toast.closed.connect(lambda t=toast: self._on_toast_closed(t))
        self._active_toasts.append(toast)

        self._reposition_all()
        toast.show_animated()
        return toast

    def _on_toast_closed(self, toast: ToastWidget) -> None:
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)
        self._reposition_all()

    def _reposition_all(self) -> None:
        """Пересчитать позиции всех toast'ов (стек снизу вверх)."""
        parent_rect = self._parent_window.rect()
        parent_global = self._parent_window.mapToGlobal(parent_rect.bottomRight())

        y_offset = 20  # отступ снизу

        for toast in reversed(self._active_toasts):
            toast.adjustSize()
            x = parent_global.x() - toast.width() - ToastWidget.MARGIN_RIGHT
            y = parent_global.y() - toast.height() - y_offset

            toast.move(QPoint(x, y))
            y_offset += toast.height() + ToastWidget.MARGIN_BOTTOM


# ─── Module-level singleton ─────────────────────────────────────────────────

_managers: dict[int, ToastManager] = {}


def get_toast_manager(parent_window: QWidget) -> ToastManager:
    """Получить (или создать) ToastManager для данного окна."""
    wid = id(parent_window)
    if wid not in _managers:
        mgr = ToastManager(parent_window)
        _managers[wid] = mgr
        # Очистить при закрытии окна
        parent_window.destroyed.connect(lambda: _managers.pop(wid, None))
    return _managers[wid]