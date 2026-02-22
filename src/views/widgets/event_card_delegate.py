"""
Event Card Delegate - делегат для рисования карточек событий в QListView.
"""

from typing import Optional
from PySide6.QtCore import Qt, QRect, QPoint, QSize, Signal
from PySide6.QtGui import QPainter, QFont, QFontMetrics, QColor, QPen, QBrush
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle

from models.domain.marker import Marker
from services.events.custom_event_manager import get_custom_event_manager


class EventCardDelegate(QStyledItemDelegate):
    """Делегат для рисования карточек событий в QListView."""

    play_clicked = Signal(int)
    edit_clicked = Signal(int)
    delete_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hovered_row = -1
        self._pressed_button = None
        self._fps = 30.0

        self._text_color = QColor("#ffffff")
        self._muted_color = QColor("#cccccc")
        self._background_color = QColor("#3a3a3a")
        self._selected_bg_color = QColor("#1a4d7a")
        self._hovered_bg_color = QColor("#4a4a4a")
        self._border_color = QColor("#555555")

        self._title_font = QFont()
        self._title_font.setBold(True)
        self._title_font.setPointSize(11)

        self._info_font = QFont()
        self._info_font.setPointSize(9)
        self._info_font.setFamily("Monospace")

    def set_fps(self, fps: float):
        self._fps = fps if fps > 0 else 30.0

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """Нарисовать элемент списка — с защитой от None."""
        painter.save()
        try:
            # FIX: Безопасное получение данных — если data() вернёт None,
            # tuple unpacking крашится с TypeError, Qt молча проглатывает,
            # и ничего не рисуется (список выглядит пустым).
            data = index.data(Qt.ItemDataRole.UserRole)
            if not data or not isinstance(data, (tuple, list)) or len(data) < 2:
                return

            original_idx, marker = data
            if marker is None:
                return

            # FIX: Получить FPS из модели (если делегату не установили)
            model_fps = index.data(Qt.ItemDataRole.UserRole + 1)
            if model_fps and isinstance(model_fps, (int, float)) and model_fps > 0:
                self._fps = float(model_fps)

            rect = option.rect
            is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
            is_hovered = (self._hovered_row == index.row())

            self._draw_background(painter, rect, is_selected, is_hovered)
            self._draw_border(painter, rect)
            self._draw_content(painter, rect, original_idx, marker, is_selected)
            self._draw_action_buttons(painter, rect, index.row(), original_idx)

        except Exception as e:
            # Никогда не допускать crash в paint() — Qt это проглотит
            # и элемент просто не отрисуется
            print(f"ERROR in EventCardDelegate.paint: {e}")

        finally:
            # FIX: painter.restore() ВСЕГДА вызывается, даже при early return
            painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index):
        return QSize(300, 80)

    def editorEvent(self, event, model, option: QStyleOptionViewItem, index):
        if event.type() == event.Type.MouseButtonPress:
            button = self._get_button_at(event.pos(), option.rect, index.row())
            if button:
                self._pressed_button = (index.row(), button)
                return True

        elif event.type() == event.Type.MouseButtonRelease:
            if self._pressed_button and self._pressed_button[0] == index.row():
                row, button_type = self._pressed_button
                data = index.data(Qt.ItemDataRole.UserRole)
                if data and isinstance(data, (tuple, list)) and len(data) >= 2:
                    original_idx, marker = data
                    if marker is not None:
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
            old_hovered = self._hovered_row
            self._hovered_row = index.row() if option.rect.contains(event.pos()) else -1
            if old_hovered != self._hovered_row:
                if old_hovered >= 0:
                    model.dataChanged.emit(model.index(old_hovered), model.index(old_hovered))
                if self._hovered_row >= 0:
                    model.dataChanged.emit(index, index)

        return super().editorEvent(event, model, option, index)

    def _draw_background(self, painter: QPainter, rect: QRect,
                         is_selected: bool, is_hovered: bool):
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
        painter.setPen(QPen(self._border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 6, 6)

    def _draw_content(self, painter: QPainter, rect: QRect,
                      original_idx: int, marker: Marker, is_selected: bool):
        content_rect = rect.adjusted(12, 8, -80, -8)
        top_y = content_rect.top() + 4

        painter.setFont(self._info_font)
        painter.setPen(QPen(self._muted_color))

        index_text = f"#{original_idx + 1}"
        painter.drawText(content_rect.left(), top_y + 12, index_text)

        fps = self._fps if self._fps > 0 else 30.0
        start_time = self._format_time(marker.start_frame / fps)
        start_x = content_rect.left() + 40
        painter.drawText(start_x, top_y + 12, start_time)

        duration_frames = max(0, marker.end_frame - marker.start_frame)
        duration_time = self._format_time(duration_frames / fps)
        duration_x = start_x + 50
        painter.drawText(duration_x, top_y + 12, duration_time)

        # Note text (if present)
        note = (marker.note or "").strip()
        if note:
            note_x = duration_x + 50
            fm = QFontMetrics(self._info_font)
            avail_w = content_rect.right() - note_x
            if avail_w > 30:
                elided = fm.elidedText(note, Qt.ElideRight, avail_w)
                painter.setPen(QPen(QColor("#aaaaaa")))
                painter.drawText(note_x, top_y + 12, elided)

        middle_y = top_y + 24

        event_color = self._get_event_color(marker.event_name)
        indicator_rect = QRect(content_rect.left(), middle_y - 6, 12, 12)
        painter.setBrush(QBrush(event_color))
        painter.setPen(QPen(event_color.darker(120), 1))
        painter.drawRoundedRect(indicator_rect, 6, 6)

        painter.setFont(self._title_font)
        text_color = QColor("#ffffff") if is_selected else self._text_color
        painter.setPen(QPen(text_color))

        event_name = self._get_event_display_name(marker.event_name)
        name_x = content_rect.left() + 20
        name_rect = QRect(name_x, middle_y - 8, content_rect.width() - 20, 20)
        painter.drawText(name_rect,
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         event_name)

    def _draw_action_buttons(self, painter: QPainter, rect: QRect,
                             row: int, original_idx: int):
        button_size = 32
        spacing = 4
        right_margin = 8

        delete_x = rect.right() - right_margin - button_size
        edit_x = delete_x - button_size - spacing
        play_x = edit_x - button_size - spacing

        button_y = rect.top() + (rect.height() - button_size) // 2

        self._draw_button(painter, QRect(play_x, button_y, button_size, button_size),
                          "▶", row, "play")
        self._draw_button(painter, QRect(edit_x, button_y, button_size, button_size),
                          "✎", row, "edit")
        self._draw_button(painter, QRect(delete_x, button_y, button_size, button_size),
                          "✕", row, "delete")

    def _draw_button(self, painter: QPainter, rect: QRect,
                     text: str, row: int, button_type: str):
        is_pressed = (self._pressed_button == (row, button_type))
        is_hovered = (self._hovered_row == row)

        if is_pressed:
            bg_color = QColor("#2a2a2a")
        elif is_hovered:
            bg_color = QColor("#4a4a4a")
        else:
            bg_color = QColor("#3a3a3a")

        painter.setPen(QPen(QColor("#666666"), 1))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 3, 3)

        painter.setFont(self._title_font)
        painter.setPen(QPen(self._text_color))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def _get_button_at(self, pos: QPoint, item_rect: QRect, row: int) -> Optional[str]:
        button_size = 32
        spacing = 4
        right_margin = 8

        delete_x = item_rect.right() - right_margin - button_size
        edit_x = delete_x - button_size - spacing
        play_x = edit_x - button_size - spacing
        button_y = item_rect.top() + (item_rect.height() - button_size) // 2

        if (play_x <= pos.x() <= play_x + button_size and
                button_y <= pos.y() <= button_y + button_size):
            return "play"
        elif (edit_x <= pos.x() <= edit_x + button_size and
              button_y <= pos.y() <= button_y + button_size):
            return "edit"
        elif (delete_x <= pos.x() <= delete_x + button_size and
              button_y <= pos.y() <= button_y + button_size):
            return "delete"
        return None

    def _get_event_color(self, event_name: str) -> QColor:
        event_manager = get_custom_event_manager()
        if event_manager:
            event = event_manager.get_event(event_name)
            if event:
                return event.get_qcolor()
        return QColor("#666666")

    def _get_event_display_name(self, event_name: str) -> str:
        event_manager = get_custom_event_manager()
        if event_manager:
            event = event_manager.get_event(event_name)
            if event:
                return event.get_localized_name()
        return event_name

    def _format_time(self, seconds: float) -> str:
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"