"""
Drawing Overlay Widget - виджет для рисования поверх видео.
Позволяет рисовать линии, прямоугольники, круги и стрелки.
"""

from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QPixmap, QPolygon
from PySide6.QtWidgets import QWidget
from typing import List, Tuple, Optional
from enum import Enum


class DrawingTool(Enum):
    """Инструменты рисования."""
    NONE = "none"
    LINE = "line"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    ARROW = "arrow"


class DrawingItem:
    """Элемент рисования."""

    def __init__(self, tool: DrawingTool, start_point: QPoint, end_point: QPoint,
                 color: QColor, thickness: int):
        self.tool = tool
        self.start_point = start_point
        self.end_point = end_point
        self.color = color
        self.thickness = thickness

    def draw(self, painter: QPainter):
        """Нарисовать элемент."""
        pen = QPen(self.color, self.thickness, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        if self.tool == DrawingTool.LINE:
            painter.drawLine(self.start_point, self.end_point)

        elif self.tool == DrawingTool.RECTANGLE:
            rect = QRect(self.start_point, self.end_point)
            painter.drawRect(rect)

        elif self.tool == DrawingTool.CIRCLE:
            rect = QRect(self.start_point, self.end_point)
            painter.drawEllipse(rect)

        elif self.tool == DrawingTool.ARROW:
            self._draw_arrow(painter)

    def _draw_arrow(self, painter: QPainter):
        """Нарисовать стрелку."""
        # Основная линия
        painter.drawLine(self.start_point, self.end_point)

        # Вычислить направление
        dx = self.end_point.x() - self.start_point.x()
        dy = self.end_point.y() - self.start_point.y()
        length = (dx**2 + dy**2)**0.5

        if length < 1:
            return

        # Нормализованный вектор направления
        nx = dx / length
        ny = dy / length

        # Перпендикулярный вектор
        px = -ny
        py = nx

        # Размер наконечника стрелки
        arrow_size = min(20, length * 0.3)

        # Точки наконечника
        tip1 = QPoint(
            int(self.end_point.x() - nx * arrow_size + px * arrow_size * 0.5),
            int(self.end_point.y() - ny * arrow_size + py * arrow_size * 0.5)
        )
        tip2 = QPoint(
            int(self.end_point.x() - nx * arrow_size - px * arrow_size * 0.5),
            int(self.end_point.y() - ny * arrow_size - py * arrow_size * 0.5)
        )

        # Нарисовать наконечник
        arrow_head = QPolygon([self.end_point, tip1, tip2])
        painter.setBrush(QBrush(self.color))
        painter.drawPolygon(arrow_head)


class DrawingOverlay(QWidget):
    """
    Виджет для рисования поверх видео.
    Обрабатывает события мыши и отображает нарисованные элементы.
    """

    # Сигналы
    drawing_changed = Signal()  # Изменение в рисовании

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)

        # Параметры рисования
        self.current_tool = DrawingTool.NONE
        self.current_color = QColor("#FF0000")  # Красный
        self.current_thickness = 2

        # Состояние рисования
        self.is_drawing = False
        self.drawing_items: List[DrawingItem] = []
        self.current_start_point: Optional[QPoint] = None
        self.current_end_point: Optional[QPoint] = None

        # Настройки прозрачности
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

    def set_tool(self, tool: DrawingTool):
        """Установить текущий инструмент рисования."""
        self.current_tool = tool
        self.update()

    def set_color(self, color: QColor):
        """Установить цвет рисования."""
        self.current_color = color

    def set_thickness(self, thickness: int):
        """Установить толщину линии."""
        self.current_thickness = thickness

    def undo(self):
        """Отменить последнее действие (удалить последний нарисованный элемент)."""
        if self.drawing_items:
            self.drawing_items.pop()  # Удалить последний элемент
            self.update()
            self.drawing_changed.emit()
            return True
        return False

    def clear_drawing(self):
        """Очистить все нарисованное."""
        self.drawing_items.clear()
        self.update()
        self.drawing_changed.emit()

    def clear_drawing_with_confirmation(self, parent_window):
        """Очистить все нарисованное с подтверждением."""
        if not self.drawing_items:
            return False

        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            parent_window,
            "Подтверждение очистки",
            f"Удалить все рисунки ({len(self.drawing_items)} элементов)?\n\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.clear_drawing()
            return True
        return False

    def paintEvent(self, event):
        """Обработка события рисования."""
        super().paintEvent(event)

        if not self.drawing_items and not self.is_drawing:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Нарисовать сохраненные элементы
        for item in self.drawing_items:
            item.draw(painter)

        # Нарисовать текущий элемент в процессе рисования
        if self.is_drawing and self.current_start_point and self.current_end_point:
            temp_item = DrawingItem(
                self.current_tool,
                self.current_start_point,
                self.current_end_point,
                self.current_color,
                self.current_thickness
            )
            temp_item.draw(painter)

    def mousePressEvent(self, event):
        """Обработка нажатия кнопки мыши."""
        if event.button() == Qt.LeftButton and self.current_tool != DrawingTool.NONE:
            self.is_drawing = True
            self.current_start_point = event.pos()
            self.current_end_point = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        """Обработка движения мыши."""
        if self.is_drawing and self.current_start_point:
            self.current_end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """Обработка отпускания кнопки мыши."""
        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False

            if self.current_start_point and self.current_end_point:
                # Создать новый элемент рисования
                item = DrawingItem(
                    self.current_tool,
                    self.current_start_point,
                    self.current_end_point,
                    self.current_color,
                    self.current_thickness
                )
                self.drawing_items.append(item)
                self.drawing_changed.emit()

            self.current_start_point = None
            self.current_end_point = None
            self.update()

    def resizeEvent(self, event):
        """Обработка изменения размера."""
        super().resizeEvent(event)
        # Можно добавить логику масштабирования существующих рисунков
        # при изменении размера видео, но пока оставим как есть
