"""
ScalableVideoLabel — виджет для отображения видео с автоматическим масштабированием.

Включает:
- Автоматическое масштабирование с сохранением пропорций
- Центрирование изображения
- Drag & Drop заглушка при отсутствии видео
- Анимация пунктирной рамки
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import (
    QPainter, QPixmap, QImage, QPaintEvent, QResizeEvent,
    QColor, QPen, QFont, QFontMetrics, QLinearGradient, QBrush
)
from PySide6.QtCore import Qt, QRect, QRectF, QSize, QTimer, QPointF
from typing import Optional
import math
import cv2
import numpy as np


class ScalableVideoLabel(QWidget):
    """
    Виджет для отображения видео с автоматическим масштабированием.

    При отсутствии видео показывает анимированную заглушку
    с пунктирной рамкой и подсказкой «Перетащите видеофайл сюда».
    """

    # ── Цвета заглушки ──
    COLOR_BG_TOP = QColor("#1a1a1a")
    COLOR_BG_BOTTOM = QColor("#111111")
    COLOR_BORDER_NORMAL = QColor("#444444")
    COLOR_BORDER_HOVER = QColor("#666666")
    COLOR_ICON = QColor("#555555")
    COLOR_ICON_HOVER = QColor("#777777")
    COLOR_TEXT_PRIMARY = QColor("#666666")
    COLOR_TEXT_PRIMARY_HOVER = QColor("#999999")
    COLOR_TEXT_SECONDARY = QColor("#444444")
    COLOR_TEXT_SECONDARY_HOVER = QColor("#666666")
    COLOR_ACCENT = QColor("#FF0000")

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Текущий кадр
        self._current_pixmap: Optional[QPixmap] = None
        self._scaled_pixmap: Optional[QPixmap] = None
        self._pixmap_rect: Optional[QRect] = None
        self._needs_scaling_update: bool = True

        # Состояние заглушки
        self._is_drag_hovering: bool = False

        # Анимация пунктирной рамки
        self._dash_offset: float = 0.0
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(50)  # 20 fps для анимации
        self._animation_timer.timeout.connect(self._on_animation_tick)

        # Пульсация иконки
        self._pulse_phase: float = 0.0

        # Настройки
        self.setMinimumSize(320, 180)
        self.setStyleSheet("background-color: black;")
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        # Запуск анимации только когда нет видео
        self._start_animation_if_needed()

    # ══════════════════════════════════════════════════════════════════
    #  Public API
    # ══════════════════════════════════════════════════════════════════

    def set_frame(self, frame) -> None:
        if frame is None:
            self._current_pixmap = None
            self._scaled_pixmap = None
            self._pixmap_rect = None
            self._needs_scaling_update = True
            self._start_animation_if_needed()
            self.update()
            return

        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self._current_pixmap = QPixmap.fromImage(qt_image)
            self._needs_scaling_update = True
            self._stop_animation()
            self.update()
        except Exception:
            self._current_pixmap = None
            self._scaled_pixmap = None
            self._pixmap_rect = None
            self._needs_scaling_update = True
            self._start_animation_if_needed()
            self.update()

    def setPixmap(self, pixmap: QPixmap) -> None:
        if pixmap is None or pixmap.isNull():
            self._current_pixmap = None
            self._scaled_pixmap = None
            self._pixmap_rect = None
            self._needs_scaling_update = True
            self._start_animation_if_needed()
        else:
            self._current_pixmap = pixmap
            self._needs_scaling_update = True
            self._stop_animation()
        self.update()

    def pixmap(self) -> Optional[QPixmap]:
        return self._current_pixmap

    def clear(self) -> None:
        self._current_pixmap = None
        self._scaled_pixmap = None
        self._pixmap_rect = None
        self._needs_scaling_update = True
        self._start_animation_if_needed()
        self.update()

    def has_video(self) -> bool:
        return self._current_pixmap is not None and not self._current_pixmap.isNull()

    # ══════════════════════════════════════════════════════════════════
    #  Drag & Drop visual feedback
    # ══════════════════════════════════════════════════════════════════

    def set_drag_hovering(self, hovering: bool) -> None:
        """Вызывается из MainWindow при dragEnterEvent/dragLeaveEvent."""
        if self._is_drag_hovering != hovering:
            self._is_drag_hovering = hovering
            self.update()

    # ══════════════════════════════════════════════════════════════════
    #  Animation
    # ══════════════════════════════════════════════════════════════════

    def _start_animation_if_needed(self) -> None:
        if not self.has_video() and not self._animation_timer.isActive():
            self._animation_timer.start()

    def _stop_animation(self) -> None:
        if self._animation_timer.isActive():
            self._animation_timer.stop()

    def _on_animation_tick(self) -> None:
        self._dash_offset = (self._dash_offset + 1) % 24
        self._pulse_phase = (self._pulse_phase + 0.08) % (2 * math.pi)
        self.update()

    # ══════════════════════════════════════════════════════════════════
    #  Events
    # ══════════════════════════════════════════════════════════════════

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._needs_scaling_update = True
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.has_video():
            self._paint_video(painter)
        else:
            self._paint_placeholder(painter)

        painter.end()

    # ══════════════════════════════════════════════════════════════════
    #  Video rendering
    # ══════════════════════════════════════════════════════════════════

    def _paint_video(self, painter: QPainter) -> None:
        if self._needs_scaling_update:
            self._update_scaling()
            self._needs_scaling_update = False

        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        if self._scaled_pixmap and not self._scaled_pixmap.isNull() and self._pixmap_rect:
            painter.drawPixmap(self._pixmap_rect, self._scaled_pixmap)

    def _update_scaling(self) -> None:
        if not self._current_pixmap or self._current_pixmap.isNull():
            self._scaled_pixmap = None
            self._pixmap_rect = None
            return

        widget_w = self.width()
        widget_h = self.height()
        pix_w = self._current_pixmap.width()
        pix_h = self._current_pixmap.height()

        scale = min(widget_w / pix_w, widget_h / pix_h)
        scaled_w = int(pix_w * scale)
        scaled_h = int(pix_h * scale)
        x = (widget_w - scaled_w) // 2
        y = (widget_h - scaled_h) // 2

        self._scaled_pixmap = self._current_pixmap.scaled(
            scaled_w, scaled_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._pixmap_rect = QRect(x, y, scaled_w, scaled_h)

    # ══════════════════════════════════════════════════════════════════
    #  Placeholder (заглушка)
    # ══════════════════════════════════════════════════════════════════

    def _paint_placeholder(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()
        is_hover = self._is_drag_hovering

        # 1. Градиентный фон
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0, self.COLOR_BG_TOP)
        gradient.setColorAt(1, self.COLOR_BG_BOTTOM)
        painter.fillRect(self.rect(), gradient)

        # 2. Пунктирная рамка с анимацией
        margin = 24
        border_rect = QRectF(margin, margin, w - margin * 2, h - margin * 2)

        border_color = self.COLOR_BORDER_HOVER if is_hover else self.COLOR_BORDER_NORMAL
        pen = QPen(border_color, 2, Qt.PenStyle.CustomDashLine)
        pen.setDashPattern([8, 6])
        pen.setDashOffset(self._dash_offset)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(border_rect, 16, 16)

        # 3. Центральная область
        cx = w / 2
        cy = h / 2

        # Пульсация
        pulse = 1.0 + 0.05 * math.sin(self._pulse_phase)
        icon_size = 48 * pulse

        # 4. Иконка 🎬 (рисуем кинохлопушку вручную)
        icon_color = self.COLOR_ICON_HOVER if is_hover else self.COLOR_ICON
        accent = self.COLOR_ACCENT if is_hover else QColor("#cc0000")
        self._draw_clapperboard_icon(painter, cx, cy - 30, icon_size, icon_color, accent)

        # 5. Основной текст
        text_color = self.COLOR_TEXT_PRIMARY_HOVER if is_hover else self.COLOR_TEXT_PRIMARY
        main_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        painter.setFont(main_font)
        painter.setPen(text_color)

        main_text = "Перетащите видеофайл сюда"
        main_rect = QRectF(0, cy + 15, w, 30)
        painter.drawText(main_rect, Qt.AlignmentFlag.AlignCenter, main_text)

        # 6. Вспомогательный текст
        sub_color = self.COLOR_TEXT_SECONDARY_HOVER if is_hover else self.COLOR_TEXT_SECONDARY
        sub_font = QFont("Segoe UI", 11)
        painter.setFont(sub_font)
        painter.setPen(sub_color)

        sub_text = "или нажмите  Файл → Открыть видео"
        sub_rect = QRectF(0, cy + 48, w, 22)
        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignCenter, sub_text)

        # 7. Форматы
        fmt_font = QFont("Segoe UI", 9)
        painter.setFont(fmt_font)
        painter.setPen(QColor("#383838"))

        fmt_text = "MP4  •  AVI  •  MOV  •  MKV  •  WMV  •  FLV"
        fmt_rect = QRectF(0, cy + 75, w, 18)
        painter.drawText(fmt_rect, Qt.AlignmentFlag.AlignCenter, fmt_text)

    def _draw_clapperboard_icon(
        self, painter: QPainter,
        cx: float, cy: float, size: float,
        color: QColor, accent: QColor
    ) -> None:
        """Нарисовать иконку кинохлопушки."""
        half = size / 2

        # Корпус (прямоугольник)
        body_rect = QRectF(cx - half, cy - half * 0.5, size, size * 0.65)
        painter.setPen(QPen(color, 2))
        painter.setBrush(QColor(color.red(), color.green(), color.blue(), 40))
        painter.drawRoundedRect(body_rect, 4, 4)

        # Хлопушка (верхняя часть — два треугольника)
        clap_y = cy - half * 0.5
        stripe_h = size * 0.22

        # Полосатая часть (3 полоски)
        stripe_w = size / 5
        for i in range(5):
            sx = cx - half + i * stripe_w
            stripe_rect = QRectF(sx, clap_y - stripe_h, stripe_w, stripe_h)
            if i % 2 == 0:
                painter.fillRect(stripe_rect, QColor(color.red(), color.green(), color.blue(), 80))
            else:
                painter.fillRect(stripe_rect, QColor(accent.red(), accent.green(), accent.blue(), 60))

        # Рамка хлопушки
        clap_rect = QRectF(cx - half, clap_y - stripe_h, size, stripe_h)
        painter.setPen(QPen(color, 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(clap_rect, 2, 2)

        # Кружок «play» в центре корпуса
        play_cx = cx
        play_cy = cy + size * 0.05
        play_r = size * 0.12

        painter.setPen(Qt.NoPen)
        painter.setBrush(accent)

        # Треугольник play
        from PySide6.QtGui import QPolygonF
        triangle = QPolygonF([
            QPointF(play_cx - play_r * 0.6, play_cy - play_r),
            QPointF(play_cx - play_r * 0.6, play_cy + play_r),
            QPointF(play_cx + play_r, play_cy),
        ])
        painter.drawPolygon(triangle)

    # ══════════════════════════════════════════════════════════════════
    #  Size hints
    # ══════════════════════════════════════════════════════════════════

    def sizeHint(self) -> QSize:
        if self._current_pixmap and not self._current_pixmap.isNull():
            return self._current_pixmap.size()
        return QSize(640, 360)

    def minimumSizeHint(self) -> QSize:
        return QSize(320, 180)