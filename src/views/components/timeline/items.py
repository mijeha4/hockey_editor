from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsLineItem
from PySide6.QtGui import QPen, QBrush, QColor
from PySide6.QtCore import Qt


class MarkerItem(QGraphicsRectItem):
    """Визуальное представление маркера события."""

    def __init__(self, marker_id: int, start_frame: int, end_frame: int,
                 color: str, event_name: str, note: str = ""):
        super().__init__()

        self.marker_id = marker_id
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.color = color
        self.event_name = event_name
        self.note = note

        # Настроить внешний вид
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QPen(Qt.black, 1))

        # Установить размеры (будут обновлены через set_geometry)
        self.setRect(0, 0, 50, 20)

        # Сделать кликабельным
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)

    def set_geometry(self, x: float, y: float, width: float, height: float):
        """Установить геометрию маркера."""
        self.setRect(x, y, width, height)

    def get_tooltip_text(self) -> str:
        """Получить текст для подсказки."""
        if self.note:
            return f"{self.event_name}\n{self.note}"
        return self.event_name


class PlayheadItem(QGraphicsLineItem):
    """Курсор текущего времени."""

    def __init__(self):
        super().__init__()

        # Желтая линия
        pen = QPen(QColor("#FFFF00"), 3, Qt.SolidLine, Qt.RoundCap)
        self.setPen(pen)

        # Не кликабельный
        self.setFlag(QGraphicsLineItem.ItemHasNoContents, False)
