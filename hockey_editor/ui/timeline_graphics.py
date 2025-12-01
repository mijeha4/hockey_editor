# ui/timeline_graphics.py
# Финальная стабильная версия — всё работает идеально

from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsScene, QGraphicsView, QGraphicsLineItem, QGraphicsTextItem,
    QScrollArea, QWidget, QVBoxLayout, QMenu
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter, QAction
from ..utils.custom_events import get_custom_event_manager


class SegmentGraphicsItem(QGraphicsRectItem):
    def __init__(self, marker, timeline_scene):
        super().__init__()
        self.marker = marker
        self.timeline_scene = timeline_scene
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)

        event_manager = get_custom_event_manager()
        event = event_manager.get_event(marker.event_name)
        self.event_color = QColor(event.color) if event else QColor("#888888")

        self.setBrush(QBrush(QColor(255, 255, 255, 230)))
        self.setPen(QPen(self.event_color, 4, Qt.SolidLine, Qt.RoundCap))

        # Использовать локализованное название события
        localized_event_name = event.get_localized_name() if event else marker.event_name
        self.text_item = QGraphicsTextItem(localized_event_name, self)
        self.text_item.setDefaultTextColor(QColor("#000000"))
        self.text_item.setFont(QFont("Segoe UI", 10, QFont.Bold))

    def paint(self, painter: QPainter, *args):
        super().paint(painter, *args)
        rect = self.rect()
        text_rect = self.text_item.boundingRect()
        x = rect.width() / 2 - text_rect.width() / 2
        y = rect.height() / 2 - text_rect.height() / 2
        self.text_item.setPos(x, y)

    def hoverEnterEvent(self, event):
        self.setPen(QPen(self.event_color.lighter(140), 6))
        self.setBrush(QBrush(QColor(255, 255, 255, 255)))

    def hoverLeaveEvent(self, event):
        self.setPen(QPen(self.event_color, 4))
        self.setBrush(QBrush(QColor(255, 255, 255, 230)))

    def mouseDoubleClickEvent(self, event):
        if self.timeline_scene.main_window:
            try:
                idx = self.timeline_scene.controller.markers.index(self.marker)
                self.timeline_scene.main_window.open_segment_editor(idx)
            except ValueError:
                pass


class TimelineGraphicsScene(QGraphicsScene):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.main_window = None
        self.pixels_per_frame = 0.8
        self.track_height = 60
        self.header_height = 40

        # Playhead создаём один раз и больше НИКОГДА не удаляем!
        self.playhead = QGraphicsLineItem()
        self.playhead.setPen(QPen(QColor("#FFFF00"), 4, Qt.SolidLine, Qt.RoundCap))
        self.playhead.setZValue(1000)
        self.addItem(self.playhead)  # добавляем навсегда

        self.rebuild()  # первый рендер

    def rebuild(self):
        total_frames = max(self.controller.get_total_frames(), 1)
        events = get_custom_event_manager().get_all_events()

        # Очищаем всё КРОМЕ playhead
        for item in self.items():
            if item is not self.playhead:
                self.removeItem(item)

        scene_width = total_frames * self.pixels_per_frame + 300
        scene_height = len(events) * self.track_height + self.header_height + 50
        self.setSceneRect(0, 0, scene_width, scene_height)

        track_bg = QColor("#0d1b2a")

        for i, event in enumerate(events):
            y = i * self.track_height

            # Фон дорожки
            self.addRect(0, y, scene_width, self.track_height,
                         QPen(Qt.NoPen), QBrush(track_bg))

            # Заголовок события
            header = self.addRect(0, y, 140, self.track_height,
                                QPen(QColor("#1b263b")), QBrush(QColor(event.color)))
            text = self.addText(event.get_localized_name())
            text.setDefaultTextColor(Qt.white)
            text.setFont(QFont("Segoe UI", 11, QFont.Bold))
            text.setPos(10, y + 15)

            # Сегменты
            for marker in self.controller.markers:
                if marker.event_name != event.name:
                    continue
                x = marker.start_frame * self.pixels_per_frame
                w = (marker.end_frame - marker.start_frame + 1) * self.pixels_per_frame
                if w < 10: w = 10

                segment = SegmentGraphicsItem(marker, self)
                segment.setRect(x + 150, y + 8, w, self.track_height - 16)
                self.addItem(segment)

        self.update_playhead(self.controller.get_current_frame_idx())

    def update_playhead(self, frame_idx: int):
        if frame_idx < 0:
            return
        x = frame_idx * self.pixels_per_frame + 150
        self.playhead.setLine(x, 0, x, self.sceneRect().height())


class TimelineWidget(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view = QGraphicsView()
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.scene = TimelineGraphicsScene(controller)
        self.scene.main_window = self  # для двойного клика
        self.view.setScene(self.scene)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.view)
        layout.addWidget(scroll)

        # === Подписки на обновления ===
        controller.markers_changed.connect(self.scene.rebuild)
        controller.playback_time_changed.connect(lambda f: self.scene.update_playhead(f))
        controller.timeline_update.connect(lambda: self.scene.update_playhead(self.controller.get_current_frame_idx()))
        get_custom_event_manager().events_changed.connect(self.scene.rebuild)

        # Масштабирование
        self.scale_factor = 1.0

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.25 if event.angleDelta().y() > 0 else 0.8
            self.scale_factor *= factor
            self.scene.pixels_per_frame *= factor
            self.scene.rebuild()

            # Автоскролл к плейхеду
            current_x = self.controller.get_current_frame_idx() * self.scene.pixels_per_frame + 150
            self.view.horizontalScrollBar().setValue(int(current_x - self.view.width() // 2))
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = self.view.mapToScene(self.view.mapFrom(self, event.pos()))
            frame = int((pos.x() - 150) / self.scene.pixels_per_frame)
            frame = max(0, min(frame, self.controller.get_total_frames() - 1))
            self.controller.seek_frame(frame)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        """Обработка правого клика - показ контекстного меню."""
        if not hasattr(self.scene, 'main_window') or not self.scene.main_window:
            return

        menu = QMenu(self)

        # Действия контекстного меню
        save_action = QAction("Сохранить проект", self)
        save_action.triggered.connect(self.scene.main_window._on_save_project)

        open_action = QAction("Открыть проект", self)
        open_action.triggered.connect(self.scene.main_window._on_open_project)

        new_action = QAction("Новый проект", self)
        new_action.triggered.connect(self.scene.main_window._on_new_project)

        menu.addAction(save_action)
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(new_action)

        # Показываем меню в позиции курсора
        menu.exec(event.globalPos())
