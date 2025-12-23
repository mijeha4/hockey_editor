from PySide6.QtWidgets import QGraphicsView
from PySide6.QtGui import QPainter, QBrush, QColor
from PySide6.QtCore import Qt
from typing import List, Dict
from .scene import TimelineScene


class TimelineView(QGraphicsView):
    """Виджет отображения таймлайна с темной темой."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Создать сцену
        self.scene = TimelineScene()
        self.setScene(self.scene)

        # Настройки отображения
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Настройки взаимодействия
        self.setDragMode(QGraphicsView.NoDrag)

        # Темная тема для сцены
        self.scene.setBackgroundBrush(QBrush(QColor("#1e1e1e")))

    def wheelEvent(self, event):
        """Обработка колесика мыши для зума."""
        if event.modifiers() & Qt.ControlModifier:
            # Ctrl + колесо = зум
            factor = 1.25 if event.angleDelta().y() > 0 else 0.8
            self.scene.set_scale(self.scene.pixels_per_frame * factor)
            event.accept()
        else:
            # Обычная прокрутка
            super().wheelEvent(event)

    def set_markers(self, markers_data: List[Dict]):
        """Установить маркеры."""
        self.scene.set_markers(markers_data)

    def set_playhead_position(self, frame: int):
        """Установить позицию плейхеда."""
        self.scene.set_playhead_position(frame)

    def set_duration(self, total_frames: int):
        """Установить общую длительность."""
        # Рассчитать ширину сцены
        scene_width = total_frames * self.scene.pixels_per_frame + 100
        scene_height = 50  # Фиксированная высота
        self.scene.setSceneRect(0, 0, scene_width, scene_height)
