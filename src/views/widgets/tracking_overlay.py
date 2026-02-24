"""
Tracking Overlay — Qt-виджет для выделения игрока мышью
и отображения результатов трекинга поверх видео.
"""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtWidgets import QWidget, QInputDialog, QMenu
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QCursor,
    QPainterPath, QFontMetrics, QMouseEvent, QPaintEvent
)

from views.styles import AppColors


class TrackingOverlay(QWidget):
    """Прозрачный оверлей для выделения и отображения трекинга.

    Режимы:
    - IDLE: Обычный режим, ничего не делает
    - SELECTING: Пользователь рисует прямоугольник выделения
    - TRACKING: Показывает результаты трекинга

    Использование:
    1. Пользователь нажимает кнопку "Выделить игрока"
    2. Overlay переходит в режим SELECTING
    3. Пользователь рисует bbox мышью
    4. Испускается сигнал player_selected с координатами
    5. Controller инициализирует трекер
    6. Overlay показывает результаты
    """

    # Сигналы
    player_selected = Signal(int, int, int, int)  # x, y, w, h (в координатах видео)
    selection_cancelled = Signal()
    track_context_menu = Signal(int, QPoint)  # track_id, screen_pos

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        # Состояние
        self._mode = "idle"  # idle, selecting, tracking
        self._selecting = False
        self._select_start: Optional[QPoint] = None
        self._select_current: Optional[QPoint] = None
        self._select_rect: Optional[QRect] = None

        # Маппинг видео → виджет
        self._video_rect: Optional[QRect] = None  # Область видео в виджете
        self._video_size: Tuple[int, int] = (1920, 1080)  # Размер видео

        # Данные трекинга для отрисовки
        self._tracked_objects: dict = {}  # track_id → TrackedObject-like dict
        self._show_trajectory = True
        self._show_labels = True

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def start_selection(self):
        """Перейти в режим выделения."""
        self._mode = "selecting"
        self.setCursor(Qt.CrossCursor)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.update()

    def cancel_selection(self):
        """Отменить выделение."""
        self._mode = "idle" if not self._tracked_objects else "tracking"
        self._selecting = False
        self._select_start = None
        self._select_current = None
        self._select_rect = None
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def set_tracking_mode(self):
        """Перейти в режим отображения трекинга."""
        self._mode = "tracking"
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setCursor(Qt.ArrowCursor)

    def set_idle_mode(self):
        """Вернуться в пассивный режим."""
        self._mode = "idle"
        self._tracked_objects.clear()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def set_video_rect(self, rect: QRect):
        """Установить область видео в виджете (для маппинга координат)."""
        self._video_rect = rect

    def set_video_size(self, width: int, height: int):
        """Установить размер оригинального видео."""
        self._video_size = (width, height)

    def update_tracked_objects(self, objects: dict):
        """Обновить отображаемые объекты.

        Args:
            objects: dict вида {track_id: {
                'bbox': (x,y,w,h), 'label': str, 'color': (r,g,b),
                'confidence': float, 'trajectory': [(x,y), ...],
                'is_active': bool
            }}
        """
        self._tracked_objects = objects
        if objects and self._mode != "selecting":
            self._mode = "tracking"
        self.update()

    def clear_tracking(self):
        """Очистить все данные трекинга."""
        self._tracked_objects.clear()
        self._mode = "idle"
        self.update()

    # ──────────────────────────────────────────────────────────────
    # Coordinate mapping
    # ──────────────────────────────────────────────────────────────

    def _widget_to_video(self, point: QPoint) -> Tuple[int, int]:
        """Конвертировать координаты виджета в координаты видео."""
        if not self._video_rect or self._video_rect.width() == 0:
            return point.x(), point.y()

        vr = self._video_rect
        vw, vh = self._video_size

        # Относительная позиция внутри области видео
        rel_x = (point.x() - vr.x()) / vr.width()
        rel_y = (point.y() - vr.y()) / vr.height()

        # В координаты видео
        video_x = int(rel_x * vw)
        video_y = int(rel_y * vh)

        return (
            max(0, min(video_x, vw - 1)),
            max(0, min(video_y, vh - 1))
        )

    def _video_to_widget(self, x: int, y: int) -> QPoint:
        """Конвертировать координаты видео в координаты виджета."""
        if not self._video_rect or self._video_size[0] == 0:
            return QPoint(x, y)

        vr = self._video_rect
        vw, vh = self._video_size

        wx = vr.x() + int((x / vw) * vr.width())
        wy = vr.y() + int((y / vh) * vr.height())

        return QPoint(wx, wy)

    def _video_rect_to_widget(self, vx: int, vy: int,
                               vw: int, vh: int) -> QRect:
        """Конвертировать bbox из координат видео в координаты виджета."""
        p1 = self._video_to_widget(vx, vy)
        p2 = self._video_to_widget(vx + vw, vy + vh)
        return QRect(p1, p2)

    # ──────────────────────────────────────────────────────────────
    # Mouse events (selection mode)
    # ──────────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if self._mode != "selecting":
            event.ignore()
            return

        if event.button() == Qt.LeftButton:
            self._selecting = True
            self._select_start = event.pos()
            self._select_current = event.pos()
            event.accept()
        elif event.button() == Qt.RightButton:
            self.cancel_selection()
            self.selection_cancelled.emit()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._mode == "selecting" and self._selecting:
            self._select_current = event.pos()
            self.update()
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._mode != "selecting" or not self._selecting:
            event.ignore()
            return

        if event.button() == Qt.LeftButton:
            self._selecting = False
            end_pos = event.pos()

            if self._select_start:
                # Вычислить прямоугольник
                rect = QRect(self._select_start, end_pos).normalized()

                # Минимальный размер
                if rect.width() > 10 and rect.height() > 10:
                    # Конвертировать в координаты видео
                    vx1, vy1 = self._widget_to_video(rect.topLeft())
                    vx2, vy2 = self._widget_to_video(rect.bottomRight())

                    video_w = vx2 - vx1
                    video_h = vy2 - vy1

                    if video_w > 5 and video_h > 5:
                        self.player_selected.emit(vx1, vy1, video_w, video_h)

            self._select_start = None
            self._select_current = None
            event.accept()

    # ──────────────────────────────────────────────────────────────
    # Painting
    # ──────────────────────────────────────────────────────────────

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._mode == "selecting":
            self._paint_selection(painter)
        elif self._mode == "tracking":
            self._paint_tracking(painter)

        painter.end()

    def _paint_selection(self, painter: QPainter):
        """Рисуем прямоугольник выделения."""
        # Затемнение фона
        painter.fillRect(self.rect(), QColor(0, 0, 0, 60))

        # Инструкция
        painter.setPen(QColor(255, 255, 255, 200))
        font = QFont("Segoe UI", 13, QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(
            self.rect(), Qt.AlignHCenter | Qt.AlignTop,
            "\n\n🎯 Выделите игрока мышью   |   ПКМ — отмена"
        )

        # Прямоугольник выделения
        if self._selecting and self._select_start and self._select_current:
            rect = QRect(self._select_start, self._select_current).normalized()

            # Полупрозрачная заливка
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(124, 58, 237, 40))
            painter.drawRect(rect)

            # Рамка
            pen = QPen(QColor(AppColors.ACCENT_LIGHT), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

            # Размер
            size_text = f"{rect.width()} × {rect.height()}"
            painter.setPen(QColor(AppColors.ACCENT_LIGHT))
            small_font = QFont("JetBrains Mono", 9)
            painter.setFont(small_font)
            painter.drawText(
                rect.x(), rect.bottom() + 16,
                size_text
            )

    def _paint_tracking(self, painter: QPainter):
        """Рисуем результаты трекинга."""
        for track_id, obj in self._tracked_objects.items():
            if not obj.get('is_active', True):
                continue

            bbox = obj.get('bbox', (0, 0, 0, 0))
            vx, vy, vw, vh = bbox
            color_rgb = obj.get('color', (124, 58, 237))
            r, g, b = color_rgb
            color = QColor(r, g, b)
            confidence = obj.get('confidence', 1.0)
            label = obj.get('label', f'#{track_id}')
            trajectory = obj.get('trajectory', [])

            # Конвертировать bbox в координаты виджета
            widget_rect = self._video_rect_to_widget(vx, vy, vw, vh)
            wx, wy = widget_rect.x(), widget_rect.y()
            ww, wh = widget_rect.width(), widget_rect.height()

            # ── Trajectory ──
            if self._show_trajectory and len(trajectory) > 1:
                for i in range(1, len(trajectory)):
                    p1 = self._video_to_widget(*trajectory[i - 1])
                    p2 = self._video_to_widget(*trajectory[i])
                    alpha = i / len(trajectory)
                    trail_color = QColor(r, g, b, int(180 * alpha))
                    pen = QPen(trail_color, max(1, int(2 * alpha)),
                               Qt.SolidLine, Qt.RoundCap)
                    painter.setPen(pen)
                    painter.drawLine(p1, p2)

            # ── Glow effect ──
            glow_color = QColor(r, g, b, 25)
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow_color)
            painter.drawRoundedRect(
                wx - 4, wy - 4, ww + 8, wh + 8, 6, 6
            )

            # ── Semi-transparent fill ──
            fill_color = QColor(r, g, b, 20)
            painter.setBrush(fill_color)
            painter.drawRect(wx, wy, ww, wh)

            # ── Border ──
            border_alpha = int(200 * confidence)
            pen = QPen(QColor(r, g, b, border_alpha), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(wx, wy, ww, wh)

            # ── Corner accents ──
            corner_len = min(15, ww // 4, wh // 4)
            accent_pen = QPen(QColor(r, g, b, 255), 3)
            painter.setPen(accent_pen)

            # Top-left
            painter.drawLine(wx, wy, wx + corner_len, wy)
            painter.drawLine(wx, wy, wx, wy + corner_len)
            # Top-right
            painter.drawLine(wx + ww, wy, wx + ww - corner_len, wy)
            painter.drawLine(wx + ww, wy, wx + ww, wy + corner_len)
            # Bottom-left
            painter.drawLine(wx, wy + wh, wx + corner_len, wy + wh)
            painter.drawLine(wx, wy + wh, wx, wy + wh - corner_len)
            # Bottom-right
            painter.drawLine(wx + ww, wy + wh, wx + ww - corner_len, wy + wh)
            painter.drawLine(wx + ww, wy + wh, wx + ww, wy + wh - corner_len)

            # ── Label badge ──
            if self._show_labels:
                font = QFont("Segoe UI", 10, QFont.Weight.Bold)
                painter.setFont(font)
                fm = QFontMetrics(font)
                text_w = fm.horizontalAdvance(label) + 12
                text_h = fm.height() + 6

                badge_x = wx
                badge_y = max(0, wy - text_h - 4)

                # Badge background
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(r, g, b, 220))
                badge_path = QPainterPath()
                badge_path.addRoundedRect(
                    QRectF(badge_x, badge_y, text_w, text_h), 4, 4
                )
                painter.drawPath(badge_path)

                # Badge text
                painter.setPen(QColor(255, 255, 255))
                painter.drawText(
                    badge_x + 6, badge_y + fm.ascent() + 3,
                    label
                )

            # ── Confidence bar ──
            if confidence < 0.8:
                bar_w = ww
                bar_h = 3
                bar_y = wy + wh + 4

                # Background
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor(60, 60, 60, 150))
                painter.drawRoundedRect(wx, bar_y, bar_w, bar_h, 1, 1)

                # Fill
                fill_w = int(bar_w * confidence)
                conf_color = QColor(r, g, b, 200) if confidence > 0.5 \
                    else QColor(245, 158, 11, 200)
                painter.setBrush(conf_color)
                painter.drawRoundedRect(wx, bar_y, fill_w, bar_h, 1, 1)