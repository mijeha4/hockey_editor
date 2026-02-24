"""
Drawing Overlay Widget - виджет для рисования поверх видео.
"""

from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QPixmap, QPolygon
from PySide6.QtWidgets import QWidget
from typing import List, Optional
from enum import Enum


class DrawingTool(Enum):
    NONE = "none"
    CURSOR = "cursor"
    LINE = "line"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    ARROW = "arrow"


class DrawingItem:
    def __init__(self, tool: DrawingTool, start_point: QPoint, end_point: QPoint,
                 color: QColor, thickness: int):
        self.tool = tool
        self.start_point = start_point
        self.end_point = end_point
        self.color = color
        self.thickness = thickness

    def draw(self, painter: QPainter):
        pen = QPen(self.color, self.thickness, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        if self.tool == DrawingTool.LINE:
            painter.drawLine(self.start_point, self.end_point)
        elif self.tool == DrawingTool.RECTANGLE:
            painter.drawRect(QRect(self.start_point, self.end_point))
        elif self.tool == DrawingTool.CIRCLE:
            painter.drawEllipse(QRect(self.start_point, self.end_point))
        elif self.tool == DrawingTool.ARROW:
            self._draw_arrow(painter)

    def _draw_arrow(self, painter: QPainter):
        painter.drawLine(self.start_point, self.end_point)

        dx = self.end_point.x() - self.start_point.x()
        dy = self.end_point.y() - self.start_point.y()
        length = (dx ** 2 + dy ** 2) ** 0.5
        if length < 1:
            return

        nx, ny = dx / length, dy / length
        px, py = -ny, nx
        arrow_size = min(20, length * 0.3)

        tip1 = QPoint(
            int(self.end_point.x() - nx * arrow_size + px * arrow_size * 0.5),
            int(self.end_point.y() - ny * arrow_size + py * arrow_size * 0.5)
        )
        tip2 = QPoint(
            int(self.end_point.x() - nx * arrow_size - px * arrow_size * 0.5),
            int(self.end_point.y() - ny * arrow_size - py * arrow_size * 0.5)
        )

        painter.setBrush(QBrush(self.color))
        painter.drawPolygon(QPolygon([self.end_point, tip1, tip2]))

    def scaled_copy(self, scale_x: float, scale_y: float) -> "DrawingItem":
        """Создать масштабированную копию для экспорта."""
        return DrawingItem(
            tool=self.tool,
            start_point=QPoint(int(self.start_point.x() * scale_x),
                               int(self.start_point.y() * scale_y)),
            end_point=QPoint(int(self.end_point.x() * scale_x),
                             int(self.end_point.y() * scale_y)),
            color=self.color,
            thickness=max(1, int(self.thickness * min(scale_x, scale_y)))
        )


class DrawingOverlay(QWidget):
    drawing_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)

        self.current_tool = DrawingTool.CURSOR
        self.current_color = QColor("#FF0000")
        self.current_thickness = 2

        self.is_drawing = False
        self.drawing_items: List[DrawingItem] = []
        self.current_start_point: Optional[QPoint] = None
        self.current_end_point: Optional[QPoint] = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

    def set_tool(self, tool):
        if isinstance(tool, DrawingTool):
            self.current_tool = tool
            return
        if isinstance(tool, str):
            value = tool.strip().lower()
            for t in DrawingTool:
                if t.value == value or t.name.lower() == value:
                    self.current_tool = t
                    return
        self.current_tool = DrawingTool.NONE

    def set_color(self, color: QColor):
        self.current_color = color

    def set_thickness(self, thickness: int):
        self.current_thickness = thickness

    def undo(self):
        if self.drawing_items:
            self.drawing_items.pop()
            self.update()
            self.drawing_changed.emit()
            return True
        return False

    def clear_drawing(self):
        self.drawing_items.clear()
        self.update()
        self.drawing_changed.emit()

    def clear_drawing_with_confirmation(self, parent_window):
        if not self.drawing_items:
            return False
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            parent_window, "Подтверждение очистки",
            f"Удалить все рисунки ({len(self.drawing_items)} элементов)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_drawing()
            return True
        return False

    # ══════════════════════════════════════════════════════════════════════
    # ★ NEW: Render drawings onto a pixmap for screenshot export
    # ══════════════════════════════════════════════════════════════════════

    def render_to_pixmap(self, base_pixmap: QPixmap) -> QPixmap:
        """Наложить все рисунки на pixmap и вернуть результат."""
        if not self.drawing_items:
            return base_pixmap.copy()

        result = base_pixmap.copy()
        painter = QPainter(result)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Масштаб: overlay size → pixmap size
        overlay_w = self.width() if self.width() > 0 else 1
        overlay_h = self.height() if self.height() > 0 else 1
        scale_x = result.width() / overlay_w
        scale_y = result.height() / overlay_h

        for item in self.drawing_items:
            scaled = item.scaled_copy(scale_x, scale_y)
            scaled.draw(painter)

        painter.end()
        return result

    def has_drawings(self) -> bool:
        return len(self.drawing_items) > 0

    # ══════════════════════════════════════════════════════════════════════
    # Paint / Mouse events
    # ══════════════════════════════════════════════════════════════════════

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.drawing_items and not self.is_drawing:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        for item in self.drawing_items:
            item.draw(painter)

        if self.is_drawing and self.current_start_point and self.current_end_point:
            temp = DrawingItem(
                self.current_tool, self.current_start_point,
                self.current_end_point, self.current_color, self.current_thickness
            )
            temp.draw(painter)

    def mousePressEvent(self, event):
        drawable = {DrawingTool.LINE, DrawingTool.RECTANGLE, DrawingTool.CIRCLE, DrawingTool.ARROW}
        if event.button() == Qt.LeftButton and self.current_tool in drawable:
            self.is_drawing = True
            self.current_start_point = event.pos()
            self.current_end_point = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_drawing and self.current_start_point:
            self.current_end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            if self.current_start_point and self.current_end_point:
                item = DrawingItem(
                    self.current_tool, self.current_start_point,
                    self.current_end_point, self.current_color, self.current_thickness
                )
                self.drawing_items.append(item)
                self.drawing_changed.emit()
            self.current_start_point = None
            self.current_end_point = None
            self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)