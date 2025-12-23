"""
Event Card Delegate - делегат для рисования карточек событий в QListView.
Заменяет QListWidget с кастомными QFrame карточками на более эффективный подход.
"""

from typing import Optional
from PySide6.QtCore import Qt, QRect, QPoint, QSize, Signal
from PySide6.QtGui import QPainter, QFont, QFontMetrics, QColor, QPen, QBrush, QPalette
from PySide6.QtWidgets import QStyledItemDelegate, QWidget, QStyleOptionViewItem, QApplication, QStyle
from ..models.marker import Marker


class EventCardDelegate(QStyledItemDelegate):
    """
    Делегат для рисования карточек событий в QListView.
    Рисует красивые карточки с информацией о событии и кнопками действий.
    """

    # Сигналы для обработки действий
    play_clicked = Signal(int)  # marker_idx
    edit_clicked = Signal(int)  # marker_idx
    delete_clicked = Signal(int)  # marker_idx

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered_row = -1
        self._pressed_button = None  # (row, button_type)
        self._fps = 30.0

        # Кэшируем цвета и шрифты для производительности
        self._text_color = QColor("#ffffff")
        self._muted_color = QColor("#cccccc")
        self._background_color = QColor("#3a3a3a")
        self._selected_bg_color = QColor("#1a4d7a")
        self._hovered_bg_color = QColor("#4a4a4a")
        self._border_color = QColor("#555555")

        # Шрифты
        self._title_font = QFont()
        self._title_font.setBold(True)
        self._title_font.setPointSize(11)

        self._info_font = QFont()
        self._info_font.setPointSize(9)
        self._info_font.setFamily("Monospace")

    def set_fps(self, fps: float):
        """Установить FPS для форматирования времени."""
        self._fps = fps

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """Нарисовать элемент списка."""
        painter.save()

        # Получить данные
        original_idx, marker = index.data(Qt.ItemDataRole.UserRole)
        if not marker:
            return

        rect = option.rect
        is_selected = option.state & QStyle.StateFlag.State_Selected
        is_hovered = (self._hovered_row == index.row())

        # Нарисовать фон карточки
        self._draw_background(painter, rect, is_selected, is_hovered)

        # Нарисовать рамку
        self._draw_border(painter, rect)

        # Нарисовать содержимое
        self._draw_content(painter, rect, original_idx, marker, is_selected)

        # Нарисовать кнопки действий
        self._draw_action_buttons(painter, rect, index.row(), original_idx)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index):
        """Вернуть рекомендуемый размер элемента."""
        return QSize(300, 80)  # Фиксированная высота для одинаковых карточек

    def editorEvent(self, event, model, option: QStyleOptionViewItem, index):
        """Обработать события мыши для кнопок."""
        if event.type() == event.Type.MouseButtonPress:
            button = self._get_button_at(event.pos(), option.rect, index.row())
            if button:
                self._pressed_button = (index.row(), button)
                return True

        elif event.type() == event.Type.MouseButtonRelease:
            if self._pressed_button and self._pressed_button[0] == index.row():
                row, button_type = self._pressed_button
                original_idx, marker = index.data(Qt.ItemDataRole.UserRole)

                if button_type == "play":
                    self.play_clicked.emit(original_idx)
                elif button_type == "edit":
                    self.edit_clicked.emit(original_idx)
                elif button_type == "delete":
                    self.delete_clicked.emit(original_idx)

                self._pressed_button = None
                return True
            self._pressed_button = None

        elif event.type() == event.Type.MouseMove:
            # Обновить hovered состояние
            old_hovered = self._hovered_row
            self._hovered_row = index.row() if option.rect.contains(event.pos()) else -1
            if old_hovered != self._hovered_row:
                # Перерисовать старый и новый hovered элементы
                if old_hovered >= 0:
                    model.dataChanged.emit(model.index(old_hovered), model.index(old_hovered))
                if self._hovered_row >= 0:
                    model.dataChanged.emit(index, index)

        return super().editorEvent(event, model, option, index)

    def _draw_background(self, painter: QPainter, rect: QRect, is_selected: bool, is_hovered: bool):
        """Нарисовать фон карточки."""
        painter.setPen(Qt.PenStyle.NoPen)

        if is_selected:
            bg_color = self._selected_bg_color
        elif is_hovered:
            bg_color = self._hovered_bg_color
        else:
            bg_color = self._background_color

        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 6, 6)

    def _draw_border(self, painter: QPainter, rect: QRect):
        """Нарисовать рамку карточки."""
        painter.setPen(QPen(self._border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 6, 6)

    def _draw_content(self, painter: QPainter, rect: QRect, original_idx: int, marker: Marker, is_selected: bool):
        """Нарисовать содержимое карточки."""
        content_rect = rect.adjusted(12, 8, -80, -8)  # Оставить место для кнопок справа

        # Верхняя строка: #1 | 00:00 | 05s
        top_y = content_rect.top() + 4

        painter.setFont(self._info_font)
        painter.setPen(QPen(self._muted_color))

        # Индекс
        index_text = f"#{original_idx + 1}"
        painter.drawText(content_rect.left(), top_y + 12, index_text)

        # Время начала
        start_time = self._format_time(marker.start_frame / self._fps if self._fps > 0 else 0)
        start_x = content_rect.left() + 40
        painter.drawText(start_x, top_y + 12, start_time)

        # Длительность
        duration_frames = marker.end_frame - marker.start_frame
        duration_time = self._format_time(duration_frames / self._fps if self._fps > 0 else 0)
        duration_x = start_x + 50
        painter.drawText(duration_x, top_y + 12, duration_time)

        # Средняя строка: цветной индикатор + название события
        middle_y = top_y + 24

        # Цветной индикатор
        indicator_rect = QRect(content_rect.left(), middle_y - 6, 12, 12)
        event_color = self._get_event_color(marker.event_name)
        painter.setBrush(QBrush(event_color))
        painter.setPen(QPen(event_color.darker(120), 1))
        painter.drawRoundedRect(indicator_rect, 6, 6)

        # Название события
        painter.setFont(self._title_font)
        text_color = self._text_color if not is_selected else QColor("#ffffff")
        painter.setPen(QPen(text_color))

        event_name = self._get_event_display_name(marker.event_name)
        name_x = content_rect.left() + 20
        name_rect = QRect(name_x, middle_y - 8, content_rect.width() - 20, 20)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, event_name)

    def _draw_action_buttons(self, painter: QPainter, rect: QRect, row: int, original_idx: int):
        """Нарисовать кнопки действий."""
        button_size = 24
        spacing = 4
        right_margin = 8

        # Позиции кнопок (справа налево)
        delete_x = rect.right() - right_margin - button_size
        edit_x = delete_x - button_size - spacing
        play_x = edit_x - button_size - spacing

        button_y = rect.top() + (rect.height() - button_size) // 2

        # Кнопка Play
        play_rect = QRect(play_x, button_y, button_size, button_size)
        self._draw_button(painter, play_rect, "▶", row, "play")

        # Кнопка Edit
        edit_rect = QRect(edit_x, button_y, button_size, button_size)
        self._draw_button(painter, edit_rect, "✏️", row, "edit")

        # Кнопка Delete
        delete_rect = QRect(delete_x, button_y, button_size, button_size)
        self._draw_button(painter, delete_rect, "🗑️", row, "delete")

    def _draw_button(self, painter: QPainter, rect: QRect, text: str, row: int, button_type: str):
        """Нарисовать кнопку."""
        is_pressed = (self._pressed_button == (row, button_type))
        is_hovered = (self._hovered_row == row)

        # Цвет фона кнопки
        if is_pressed:
            bg_color = QColor("#2a2a2a")
        elif is_hovered:
            bg_color = QColor("#4a4a4a")
        else:
            bg_color = QColor("#3a3a3a")

        # Рамка
        border_color = QColor("#666666")

        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 3, 3)

        # Текст кнопки
        painter.setFont(self._info_font)
        painter.setPen(QPen(self._text_color))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _get_button_at(self, pos: QPoint, item_rect: QRect, row: int) -> Optional[str]:
        """Определить, какая кнопка находится в данной позиции."""
        button_size = 24
        spacing = 4
        right_margin = 8

        delete_x = item_rect.right() - right_margin - button_size
        edit_x = delete_x - button_size - spacing
        play_x = edit_x - button_size - spacing

        button_y = item_rect.top() + (item_rect.height() - button_size) // 2

        if play_x <= pos.x() <= play_x + button_size and button_y <= pos.y() <= button_y + button_size:
            return "play"
        elif edit_x <= pos.x() <= edit_x + button_size and button_y <= pos.y() <= button_y + button_size:
            return "edit"
        elif delete_x <= pos.x() <= delete_x + button_size and button_y <= pos.y() <= button_y + button_size:
            return "delete"

        return None

    def _get_event_color(self, event_name: str) -> QColor:
        """Получить цвет для события."""
        from ..utils.custom_events import get_custom_event_manager
        event_manager = get_custom_event_manager()
        event = event_manager.get_event(event_name)
        if event:
            return event.get_qcolor()
        return QColor("#666666")

    def _get_event_display_name(self, event_name: str) -> str:
        """Получить отображаемое имя события."""
        from ..utils.custom_events import get_custom_event_manager
        event_manager = get_custom_event_manager()
        event = event_manager.get_event(event_name)
        if event:
            return event.get_localized_name()
        return event_name

    def _format_time(self, seconds: float) -> str:
        """Форматировать время в MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"
