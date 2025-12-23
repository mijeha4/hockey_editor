from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtCore import Signal, QObject
from typing import List, Dict
from .items import MarkerItem, PlayheadItem


class TimelineScene(QGraphicsScene):
    """Сцена таймлайна с маркерами и плейхедом."""

    # Сигналы
    marker_clicked = Signal(int)  # marker_id
    marker_moved = Signal(int, int, int)  # marker_id, new_start, new_end

    def __init__(self, parent=None):
        super().__init__(parent)

        # Создать плейхед
        self.playhead = PlayheadItem()
        self.addItem(self.playhead)

        # Хранилище маркеров
        self.marker_items = {}  # marker_id -> MarkerItem

        # Настройки масштаба
        self.pixels_per_frame = 0.5
        self.track_height = 30

    def set_markers(self, markers_data: List[Dict]):
        """
        Установить маркеры.
        markers_data: [{'id': int, 'start_frame': int, 'end_frame': int,
                       'color': str, 'event_name': str, 'note': str}, ...]
        """
        # Очистить старые маркеры (кроме плейхеда)
        for item in self.items():
            if item != self.playhead:
                self.removeItem(item)

        self.marker_items.clear()

        # Создать новые маркеры
        y_offset = 10  # Отступ от верха

        for marker_data in markers_data:
            marker_id = marker_data['id']
            start_frame = marker_data['start_frame']
            end_frame = marker_data['end_frame']
            color = marker_data['color']
            event_name = marker_data['event_name']
            note = marker_data.get('note', '')

            # Создать элемент
            marker_item = MarkerItem(marker_id, start_frame, end_frame,
                                   color, event_name, note)

            # Рассчитать позицию и размер
            x = start_frame * self.pixels_per_frame
            width = (end_frame - start_frame + 1) * self.pixels_per_frame
            if width < 10:
                width = 10

            marker_item.set_geometry(x, y_offset, width, self.track_height)
            marker_item.setToolTip(marker_item.get_tooltip_text())

            # Добавить на сцену
            self.addItem(marker_item)
            self.marker_items[marker_id] = marker_item

    def set_playhead_position(self, frame: int):
        """Установить позицию плейхеда."""
        x = frame * self.pixels_per_frame
        scene_height = self.sceneRect().height()
        self.playhead.setLine(x, 0, x, scene_height)

    def set_scale(self, pixels_per_frame: float):
        """Установить масштаб."""
        self.pixels_per_frame = pixels_per_frame
        # Перерисовать все элементы
        self._update_all_items()

    def _update_all_items(self):
        """Обновить позиции всех элементов."""
        # Обновить маркеры
        for marker_item in self.marker_items.values():
            x = marker_item.start_frame * self.pixels_per_frame
            width = (marker_item.end_frame - marker_item.start_frame + 1) * self.pixels_per_frame
            if width < 10:
                width = 10

            rect = marker_item.rect()
            marker_item.set_geometry(x, rect.y(), width, rect.height())

        # Обновить плейхед
        if hasattr(self, 'current_frame'):
            self.set_playhead_position(self.current_frame)

    def mousePressEvent(self, event):
        """Обработка клика мыши."""
        super().mousePressEvent(event)

        # Проверить, кликнули ли на маркер
        clicked_items = self.items(event.scenePos())
        for item in clicked_items:
            if isinstance(item, MarkerItem):
                self.marker_clicked.emit(item.marker_id)
                break
