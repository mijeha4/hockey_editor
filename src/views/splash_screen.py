"""
Splash Screen — загрузочный экран Hockey Editor Pro.
Рисуется полностью через QPainter (без внешних изображений).
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPixmap,
    QLinearGradient, QRadialGradient, QPainterPath, QFontMetrics, QIcon
)
from PySide6.QtCore import Qt, QRect, QRectF, QTimer, QSize, QPointF


class SplashScreen(QWidget):
    """Загрузочный экран приложения."""

    WIDTH = 520
    HEIGHT = 340

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        # Центрировать на экране
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + (geo.width() - self.WIDTH) // 2,
                geo.y() + (geo.height() - self.HEIGHT) // 2,
            )

        self._progress: float = 0.0
        self._status_text: str = "Запуск..."
        self._version: str = "1.0.0"
        self._fade_opacity: float = 1.0

    # ─── Public API ──────────────────────────────────────────────────

    def set_progress(self, value: float, status: str = "") -> None:
        """Установить прогресс (0.0 — 1.0) и текст статуса."""
        self._progress = max(0.0, min(1.0, value))
        if status:
            self._status_text = status
        self.update()
        QApplication.processEvents()

    def set_version(self, version: str) -> None:
        self._version = version

    def finish_and_close(self, delay_ms: int = 400) -> None:
        """Завершить splash screen с небольшой задержкой."""
        self.set_progress(1.0, "Готово!")
        QTimer.singleShot(delay_ms, self.close)

    # ─── Painting ────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setOpacity(self._fade_opacity)

        w, h = self.WIDTH, self.HEIGHT

        # ── Фон с тенью ──
        # Тень
        shadow_rect = QRectF(4, 4, w - 4, h - 4)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 80))
        p.drawRoundedRect(shadow_rect, 14, 14)

        # Основной фон
        bg_rect = QRectF(0, 0, w - 8, h - 8)
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0.0, QColor("#0d1117"))
        bg_grad.setColorAt(0.4, QColor("#161b22"))
        bg_grad.setColorAt(1.0, QColor("#0d1117"))
        p.setBrush(QBrush(bg_grad))
        p.setPen(QPen(QColor("#30363d"), 1))
        p.drawRoundedRect(bg_rect, 12, 12)

        content_w = w - 8

        # ── Декоративная линия сверху (акцент) ──
        accent_grad = QLinearGradient(40, 0, content_w - 40, 0)
        accent_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        accent_grad.setColorAt(0.2, QColor("#1565c0"))
        accent_grad.setColorAt(0.5, QColor("#4fc3f7"))
        accent_grad.setColorAt(0.8, QColor("#1565c0"))
        accent_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(QPen(QBrush(accent_grad), 2))
        p.drawLine(40, 2, content_w - 40, 2)

        # ── Иконка (мини-версия) ──
        self._draw_mini_icon(p, int(content_w // 2 - 28), 30, 56)

        # ── Название приложения ──
        title_font = QFont("Segoe UI", 24, QFont.Bold)
        p.setFont(title_font)
        p.setPen(QColor("#ffffff"))

        title_rect = QRect(0, 95, content_w, 40)
        p.drawText(title_rect, Qt.AlignCenter, "Hockey Editor")

        # ── "Pro" badge ──
        pro_font = QFont("Segoe UI", 11, QFont.Bold)
        p.setFont(pro_font)
        fm = QFontMetrics(pro_font)
        pro_text = "PRO"
        pro_w = fm.horizontalAdvance(pro_text) + 12
        pro_h = fm.height() + 4
        pro_x = content_w // 2 + fm.horizontalAdvance("Hockey Editor") // 2 - 40
        pro_y = 100

        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#1565c0"))
        p.drawRoundedRect(pro_x, pro_y, pro_w, pro_h, 4, 4)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRect(pro_x, pro_y, pro_w, pro_h), Qt.AlignCenter, pro_text)

        # ── Подзаголовок ──
        sub_font = QFont("Segoe UI", 10)
        p.setFont(sub_font)
        p.setPen(QColor("#8b949e"))
        sub_rect = QRect(0, 140, content_w, 20)
        p.drawText(sub_rect, Qt.AlignCenter, "Профессиональный видеоредактор для хоккея")

        # ── Версия ──
        ver_font = QFont("Segoe UI", 9)
        p.setFont(ver_font)
        p.setPen(QColor("#484f58"))
        ver_rect = QRect(0, 165, content_w, 18)
        p.drawText(ver_rect, Qt.AlignCenter, f"Версия {self._version}")

        # ── Декоративные элементы (лёд) ──
        self._draw_ice_particles(p, content_w, h)

        # ── Прогресс-бар ──
        bar_margin = 40
        bar_y = h - 70
        bar_w = content_w - bar_margin * 2
        bar_h = 6

        # Фон бара
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#21262d"))
        p.drawRoundedRect(bar_margin, bar_y, bar_w, bar_h, 3, 3)

        # Заполнение
        if self._progress > 0:
            fill_w = int(bar_w * self._progress)
            fill_grad = QLinearGradient(bar_margin, 0, bar_margin + fill_w, 0)
            fill_grad.setColorAt(0.0, QColor("#1565c0"))
            fill_grad.setColorAt(1.0, QColor("#4fc3f7"))
            p.setBrush(QBrush(fill_grad))
            p.drawRoundedRect(bar_margin, bar_y, fill_w, bar_h, 3, 3)

        # ── Текст статуса ──
        status_font = QFont("Segoe UI", 9)
        p.setFont(status_font)
        p.setPen(QColor("#8b949e"))
        status_rect = QRect(bar_margin, bar_y + 12, bar_w, 20)
        p.drawText(status_rect, Qt.AlignLeft | Qt.AlignVCenter, self._status_text)

        # ── Процент ──
        pct_text = f"{int(self._progress * 100)}%"
        p.drawText(status_rect, Qt.AlignRight | Qt.AlignVCenter, pct_text)

        # ── Copyright ──
        copy_font = QFont("Segoe UI", 8)
        p.setFont(copy_font)
        p.setPen(QColor("#30363d"))
        copy_rect = QRect(0, h - 28, content_w, 16)
        p.drawText(copy_rect, Qt.AlignCenter, "© 2024 Hockey Editor Pro")

        p.end()

    def _draw_mini_icon(self, p: QPainter, x: int, y: int, size: int) -> None:
        """Нарисовать мини-иконку (клюшка + шайба)."""
        p.save()
        p.translate(x, y)

        s = size

        # Фон
        grad = QLinearGradient(0, 0, s, s)
        grad.setColorAt(0.0, QColor("#0d47a1"))
        grad.setColorAt(1.0, QColor("#1565c0"))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        radius = int(s * 0.2)
        p.drawRoundedRect(0, 0, s, s, radius, radius)

        # Клюшка
        stick_pen = QPen(QColor("#ffffff"), max(2, int(s * 0.05)))
        stick_pen.setCapStyle(Qt.RoundCap)
        p.setPen(stick_pen)
        p.setBrush(Qt.NoBrush)

        path = QPainterPath()
        path.moveTo(s * 0.65, s * 0.15)
        path.lineTo(s * 0.38, s * 0.58)
        path.quadTo(QPointF(s * 0.30, s * 0.63), QPointF(s * 0.22, s * 0.62))
        p.drawPath(path)

        # Шайба
        p.setPen(QPen(QColor("#555"), max(1, int(s * 0.01))))
        p.setBrush(QColor("#222222"))
        p.drawEllipse(int(s * 0.25), int(s * 0.68), int(s * 0.50), int(s * 0.14))

        # Play
        play_path = QPainterPath()
        cx, cy = s * 0.62, s * 0.40
        ps = s * 0.16
        play_path.moveTo(cx - ps * 0.4, cy - ps * 0.5)
        play_path.lineTo(cx + ps * 0.5, cy)
        play_path.lineTo(cx - ps * 0.4, cy + ps * 0.5)
        play_path.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#4fc3f7"))
        p.drawPath(play_path)

        p.restore()

    def _draw_ice_particles(self, p: QPainter, w: int, h: int) -> None:
        """Декоративные частицы «льда»."""
        p.setPen(Qt.NoPen)

        particles = [
            (0.12, 0.55, 2, 15), (0.88, 0.48, 3, 10),
            (0.25, 0.72, 2, 12), (0.75, 0.65, 1, 18),
            (0.08, 0.80, 2, 8),  (0.92, 0.75, 2, 14),
            (0.50, 0.58, 1, 10), (0.35, 0.82, 2, 6),
        ]

        for px, py, radius, alpha in particles:
            p.setBrush(QColor(79, 195, 247, alpha))
            p.drawEllipse(QPointF(w * px, h * py), radius, radius)