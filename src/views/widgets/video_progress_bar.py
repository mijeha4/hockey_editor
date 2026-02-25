"""
VideoProgressBar — YouTube-style прогресс-бар видео.

Особенности:
- Тонкая полоска (3px), увеличивается при наведении (5px)
- Красная заливка текущей позиции
- Белый круглый handle при наведении
- Tooltip с временем при наведении
- Click/drag для перемотки
"""

from __future__ import annotations

from typing import Optional, List, Tuple

from PySide6.QtCore import Qt, Signal, QTimer, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QFontMetrics,
    QPaintEvent, QMouseEvent, QEnterEvent
)
from PySide6.QtWidgets import QWidget


class VideoProgressBar(QWidget):
    """YouTube-style прогресс-бар для видео."""

    seek_requested = Signal(int)    # frame index
    drag_started = Signal()
    drag_ended = Signal()

    # ── Размеры ──
    WIDGET_HEIGHT = 55
    BAR_HEIGHT_NORMAL = 3
    BAR_HEIGHT_HOVER = 5
    HANDLE_RADIUS_NORMAL = 0     # скрыт
    HANDLE_RADIUS_HOVER = 7
    TOOLTIP_HEIGHT = 22
    TOOLTIP_PADDING_H = 8
    TOOLTIP_MARGIN_BOTTOM = 4
    TOOLTIP_RADIUS = 4

    # ── Цвета ──
    COLOR_BG = QColor("#3a3a3a")
    COLOR_BUFFER = QColor("#555555")
    COLOR_PROGRESS = QColor("#FF0000")
    COLOR_HANDLE_FILL = QColor("#FF0000")
    COLOR_HANDLE_BORDER = QColor("#FFFFFF")
    COLOR_HOVER_PREVIEW = QColor(255, 255, 255, 40)
    COLOR_TOOLTIP_BG = QColor("#0a0a0a")
    COLOR_TOOLTIP_TEXT = QColor("#ffffff")
    COLOR_TOOLTIP_BORDER = QColor("#555555")
    COLOR_CHAPTER_MARK = QColor(255, 255, 255, 80)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(self.WIDGET_HEIGHT)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._total_frames: int = 0
        self._current_frame: int = 0
        self._fps: float = 30.0

        self._is_hovered: bool = False
        self._is_dragging: bool = False
        self._hover_x: int = 0
        self._hover_ratio: float = 0.0

        # Маркеры сегментов (опционально — тонкие вертикальные чёрточки)
        self._chapter_frames: List[int] = []

        # Debounce для seek при drag
        self._seek_timer = QTimer(self)
        self._seek_timer.setSingleShot(True)
        self._seek_timer.setInterval(30)
        self._seek_timer.timeout.connect(self._emit_pending_seek)
        self._pending_seek_frame: int = 0

        # Tooltip font
        self._tooltip_font = QFont("Consolas", 9)
        self._tooltip_fm = QFontMetrics(self._tooltip_font)

    # ══════════════════════════════════════════════════════════════════
    #  Public API
    # ══════════════════════════════════════════════════════════════════

    def set_total_frames(self, total: int) -> None:
        self._total_frames = max(0, total)
        self.update()

    def set_current_frame(self, frame: int) -> None:
        if self._is_dragging:
            return
        self._current_frame = max(0, min(frame, self._total_frames))
        self.update()

    def set_fps(self, fps: float) -> None:
        self._fps = fps if fps > 0 else 30.0

    def set_chapter_frames(self, frames: List[int]) -> None:
        """Установить позиции разделителей (начала сегментов)."""
        self._chapter_frames = sorted(set(frames))
        self.update()

    # ══════════════════════════════════════════════════════════════════
    #  Geometry helpers
    # ══════════════════════════════════════════════════════════════════

    def _bar_rect(self) -> QRectF:
        """Прямоугольник самой полоски."""
        h = self.BAR_HEIGHT_HOVER if self._is_hovered or self._is_dragging else self.BAR_HEIGHT_NORMAL
        y = (self.height() - h) / 2.0 + 3  # чуть ниже центра, чтобы tooltip не обрезался
        return QRectF(0, y, self.width(), h)

    def _x_to_ratio(self, x: float) -> float:
        w = self.width()
        if w <= 0:
            return 0.0
        return max(0.0, min(1.0, x / w))

    def _ratio_to_frame(self, ratio: float) -> int:
        if self._total_frames <= 0:
            return 0
        return int(ratio * (self._total_frames - 1))

    def _frame_to_x(self, frame: int) -> float:
        if self._total_frames <= 1:
            return 0.0
        return (frame / (self._total_frames - 1)) * self.width()

    def _progress_ratio(self) -> float:
        if self._total_frames <= 1:
            return 0.0
        return self._current_frame / (self._total_frames - 1)

    # ══════════════════════════════════════════════════════════════════
    #  Paint
    # ══════════════════════════════════════════════════════════════════

    def paintEvent(self, event: QPaintEvent) -> None:
        if self._total_frames <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bar = self._bar_rect()
        progress = self._progress_ratio()
        is_active = self._is_hovered or self._is_dragging

        # 1. Фон полоски (буферизованная часть = вся длина)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.COLOR_BUFFER)
        painter.drawRoundedRect(bar, bar.height() / 2, bar.height() / 2)

        # 2. Прогресс (красная часть)
        if progress > 0:
            progress_rect = QRectF(bar.left(), bar.top(), bar.width() * progress, bar.height())
            painter.setBrush(self.COLOR_PROGRESS)
            painter.drawRoundedRect(progress_rect, bar.height() / 2, bar.height() / 2)

        # 3. Hover preview (полупрозрачная зона от прогресса до мыши)
        if is_active and not self._is_dragging:
            hover_x = self._hover_x
            prog_x = bar.width() * progress
            if hover_x > prog_x:
                preview_rect = QRectF(prog_x, bar.top(), hover_x - prog_x, bar.height())
                painter.setBrush(self.COLOR_HOVER_PREVIEW)
                painter.drawRect(preview_rect)

        # 4. Chapter marks (тонкие разделители)
        if self._chapter_frames and self._total_frames > 1:
            painter.setPen(QPen(self.COLOR_CHAPTER_MARK, 1))
            for cf in self._chapter_frames:
                cx = self._frame_to_x(cf)
                painter.drawLine(
                    QPointF(cx, bar.top()),
                    QPointF(cx, bar.bottom())
                )
            painter.setPen(Qt.NoPen)

        # 5. Handle (красный кружок)
        if is_active:
            handle_x = bar.width() * progress
            handle_y = bar.center().y()
            r = self.HANDLE_RADIUS_HOVER

            # Белая обводка
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(self.COLOR_HANDLE_BORDER, 1.5))
            painter.drawEllipse(QPointF(handle_x, handle_y), r, r)

            # Красная заливка
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.COLOR_HANDLE_FILL)
            painter.drawEllipse(QPointF(handle_x, handle_y), r - 1.5, r - 1.5)

        # 6. Time tooltip (при hover)
        if self._is_hovered and not self._is_dragging:
            self._paint_time_tooltip(painter, self._hover_x, self._hover_ratio)
        elif self._is_dragging:
            drag_ratio = self._x_to_ratio(self._hover_x)
            self._paint_time_tooltip(painter, self._hover_x, drag_ratio)

        painter.end()

    def _paint_time_tooltip(self, painter: QPainter, x: float, ratio: float) -> None:
        """Рисуем мини-tooltip с временем над позицией мыши."""
        frame = self._ratio_to_frame(ratio)
        time_text = self._format_time(frame / self._fps if self._fps > 0 else 0)

        text_w = self._tooltip_fm.horizontalAdvance(time_text)
        tooltip_w = text_w + self.TOOLTIP_PADDING_H * 2
        tooltip_h = self.TOOLTIP_HEIGHT

        bar = self._bar_rect()
        tooltip_x = x - tooltip_w / 2
        tooltip_y = bar.top() - tooltip_h - self.TOOLTIP_MARGIN_BOTTOM

        # Не выходить за границы виджета
        tooltip_x = max(2, min(tooltip_x, self.width() - tooltip_w - 2))

        tooltip_rect = QRectF(tooltip_x, tooltip_y, tooltip_w, tooltip_h)

        # Фон
        painter.setPen(QPen(self.COLOR_TOOLTIP_BORDER, 1))
        painter.setBrush(self.COLOR_TOOLTIP_BG)
        painter.drawRoundedRect(tooltip_rect, self.TOOLTIP_RADIUS, self.TOOLTIP_RADIUS)

        # Текст
        painter.setPen(self.COLOR_TOOLTIP_TEXT)
        painter.setFont(self._tooltip_font)
        painter.drawText(tooltip_rect, Qt.AlignmentFlag.AlignCenter, time_text)

    # ══════════════════════════════════════════════════════════════════
    #  Mouse events
    # ══════════════════════════════════════════════════════════════════

    def enterEvent(self, event: QEnterEvent) -> None:
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._is_hovered = False
        if not self._is_dragging:
            self.update()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._hover_x = event.position().x()
        self._hover_ratio = self._x_to_ratio(self._hover_x)

        if self._is_dragging:
            frame = self._ratio_to_frame(self._hover_ratio)
            self._current_frame = frame
            self._schedule_seek(frame)

        self.update()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._total_frames > 0:
            self._is_dragging = True
            self.drag_started.emit()

            ratio = self._x_to_ratio(event.position().x())
            frame = self._ratio_to_frame(ratio)
            self._current_frame = frame
            self._hover_x = event.position().x()
            self._emit_seek_now(frame)
            self.update()

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False

            # Финальный seek
            ratio = self._x_to_ratio(event.position().x())
            frame = self._ratio_to_frame(ratio)
            self._seek_timer.stop()
            self._emit_seek_now(frame)

            self.drag_ended.emit()
            self.update()

        super().mouseReleaseEvent(event)

    # ══════════════════════════════════════════════════════════════════
    #  Seek helpers
    # ══════════════════════════════════════════════════════════════════

    def _schedule_seek(self, frame: int) -> None:
        """Запланировать seek с debounce."""
        self._pending_seek_frame = frame
        if not self._seek_timer.isActive():
            self._seek_timer.start()

    def _emit_pending_seek(self) -> None:
        self.seek_requested.emit(self._pending_seek_frame)

    def _emit_seek_now(self, frame: int) -> None:
        self._pending_seek_frame = frame
        self.seek_requested.emit(frame)

    # ══════════════════════════════════════════════════════════════════
    #  Time formatting
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _format_time(seconds: float) -> str:
        s = max(0, int(seconds))
        if s >= 3600:
            return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"
        return f"{s // 60}:{s % 60:02d}"