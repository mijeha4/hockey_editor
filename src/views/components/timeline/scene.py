from PySide6.QtWidgets import QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem
from PySide6.QtCore import Signal, QObject, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPen
from typing import List, Dict
from .items import MarkerItem, PlayheadItem


class TimelineScene(QGraphicsScene):
    """Сцена таймлайна с маркерами, дорожками и плейхедом."""

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

        # Хранилище элементов фона дорожек
        self.track_backgrounds = []  # Список QGraphicsRectItem для фона
        self.track_headers = []      # Список QGraphicsTextItem для заголовков

        # Настройки масштаба
        self.pixels_per_frame = 0.5
        self.track_height = 30

    def init_tracks(self, event_types: List, duration_frames: int):
        """
        Инициализировать дорожки с фоном и заголовками.

        Args:
            event_types: Список EventType объектов
            duration_frames: Общая длительность видео в кадрах
        """
        # Очистить старые элементы фона (но не маркеры и плейхед!)
        for item in self.track_backgrounds:
            self.removeItem(item)
        for item in self.track_headers:
            self.removeItem(item)

        self.track_backgrounds.clear()
        self.track_headers.clear()

        # Рассчитать ширину сцены
        scene_width = duration_frames * self.pixels_per_frame + 200  # +200 для заголовков

        # Цвета фона дорожек (зебра)
        track_colors = [QColor("#2b2b2b"), QColor("#333333")]  # Темный и чуть светлее

        for i, event_type in enumerate(event_types):
            # Рассчитать Y-позицию дорожки
            y = i * self.track_height + 10

            # Создать фон дорожки (длинный прямоугольник)
            track_rect = QRectF(120, y, scene_width - 120, self.track_height)  # 120 - место для заголовков
            background = QGraphicsRectItem(track_rect)

            # Установить цвет фона (чередование)
            background.setBrush(QBrush(track_colors[i % 2]))
            background.setPen(QPen(Qt.PenStyle.NoPen))  # Без границы

            # Z-index: 0 (фон ниже всего)
            background.setZValue(0)

            self.addItem(background)
            self.track_backgrounds.append(background)

            # Создать заголовок дорожки
            header_text = QGraphicsTextItem(event_type.name)
            header_text.setPos(10, y + 5)  # Смещение для центрирования

            # Стилизация текста
            header_text.setDefaultTextColor(QColor("#ffffff"))
            font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            header_text.setFont(font)

            # Z-index: 0 (фон)
            header_text.setZValue(0)

            self.addItem(header_text)
            self.track_headers.append(header_text)

    def set_markers(self, markers_data: List[Dict]):
        """
        Установить маркеры.
        markers_data: [{'id': int, 'start_frame': int, 'end_frame': int,
                       'color': str, 'event_name': str, 'note': str, 'track_index': int}, ...]
        """
        # Очистить старые маркеры (кроме плейхеда)
        for item in self.items():
            if item != self.playhead:
                self.removeItem(item)

        self.marker_items.clear()

        # Создать новые маркеры
        for marker_data in markers_data:
            marker_id = marker_data['id']
            start_frame = marker_data['start_frame']
            end_frame = marker_data['end_frame']
            color = marker_data['color']
            event_name = marker_data['event_name']
            note = marker_data.get('note', '')
            track_index = marker_data.get('track_index', 0)  # Индекс дорожки

            # Создать элемент
            marker_item = MarkerItem(marker_id, start_frame, end_frame,
                                   color, event_name, note)

            # Рассчитать позицию и размер
            x = start_frame * self.pixels_per_frame
            width = (end_frame - start_frame + 1) * self.pixels_per_frame
            if width < 10:
                width = 10

            # Рассчитать Y-позицию на основе индекса дорожки
            y = track_index * self.track_height + 10  # 10 - отступ от верха

            marker_item.set_geometry(x, y, width, self.track_height)
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
