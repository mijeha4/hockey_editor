"""
Timeline Scene Widget - Multi-track timeline for hockey events.

Displays vertical tracks for different event types with horizontal time ruler,
red current time line, and colored event rectangles.

FIXED: Added re-entrance guard in rebuild() and defensive copy of markers list.
"""

from typing import List, Optional, Dict
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsLineItem, QGraphicsPolygonItem, QFrame
)
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter, QPolygonF
from PySide6.QtCore import Qt, QRectF, QPointF, Signal

try:
    from views.styles import AppColors
    from models.domain.marker import Marker
except ImportError:
    from ..styles import AppColors
    from ...models.domain.marker import Marker


class EventItem(QGraphicsRectItem):
    """Rectangle item representing an event on a track."""

    EVENT_COLORS = {
        "Гол": QColor(255, 100, 100),
        "Бросок в створ": QColor(100, 150, 255),
        "Бросок мимо": QColor(150, 150, 150),
        "Удаление": QColor(255, 200, 100),
        "Вброс": QColor(100, 255, 100),
        "Перехват": QColor(200, 100, 255),
        "Блокшот": QColor(255, 150, 50),
        "Блокшот в обороне": QColor(255, 150, 50),
        "Вбрасывание: Проиграно": QColor(255, 100, 100),
        "Вбрасывание: Пропущено": QColor(100, 255, 100),
        "Потеря": QColor(200, 200, 100),
        "Вход в зону": QColor(150, 200, 255),
        "Выход из зоны": QColor(150, 200, 255),
        "Заблокировано": QColor(100, 100, 150),
    }

    def __init__(self, marker: Marker, track_index: int, pixels_per_second: float,
                 track_height: int, ruler_height: int, fps: float = 30.0, parent=None):
        super().__init__(parent)
        self.marker = marker
        self.track_index = track_index
        self.pixels_per_second = pixels_per_second
        self.track_height = track_height
        self.ruler_height = ruler_height
        self.fps = fps
        self.is_selected = False

        start_sec = marker.start_frame / fps
        duration_sec = (marker.end_frame - marker.start_frame) / fps
        y = ruler_height + track_index * track_height + 4
        x = start_sec * pixels_per_second
        w = max(duration_sec * pixels_per_second, 12)
        h = track_height - 8

        self.setRect(x, y, w, h)

        self.normal_color = self._get_event_color(marker)
        self.hover_color = self.normal_color.lighter(120)
        self.selected_color = self.normal_color.lighter(150)

        color_with_alpha = QColor(self.normal_color)
        color_with_alpha.setAlpha(180)
        self.setBrush(QBrush(color_with_alpha))
        self.setPen(QPen(QColor(60, 60, 60), 1))

        self._add_label(marker, x, y, w, h)

    def _add_label(self, marker: Marker, x: float, y: float, w: float, h: float):
        label_text = marker.note if marker.note else marker.event_name[:10]
        text = QGraphicsTextItem(label_text, self)
        text.setDefaultTextColor(Qt.white)
        text.setFont(QFont("Segoe UI", 8))
        text.setPos(x + 2, y + 2)

        text_rect = text.boundingRect()
        if text_rect.width() > w - 4:
            while text_rect.width() > w - 4 and len(label_text) > 3:
                label_text = label_text[:-1]
                text.setPlainText(label_text + "...")
                text_rect = text.boundingRect()

        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, event):
        if not self.is_selected:
            self.setBrush(QBrush(self.hover_color))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if not self.is_selected:
            self.setBrush(QBrush(self.normal_color))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_selected(not self.is_selected)
            if hasattr(self.scene(), 'event_selected'):
                self.scene().event_selected.emit(self.marker)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self.scene(), 'event_double_clicked'):
                self.scene().event_double_clicked.emit(self.marker)
        super().mouseDoubleClickEvent(event)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self.setBrush(QBrush(self.selected_color))
            self.setPen(QPen(QColor(255, 255, 255), 2))
        else:
            self.setBrush(QBrush(self.normal_color))
            self.setPen(QPen(QColor(60, 60, 60), 1))

    def _get_event_color(self, marker: Marker) -> QColor:
        if hasattr(marker, '_display_color') and marker._display_color:
            return marker._display_color
        try:
            from services.events.custom_event_manager import get_custom_event_manager
            event_manager = get_custom_event_manager()
            if event_manager:
                event = event_manager.get_event(marker.event_name)
                if event:
                    return QColor(event.color)
        except ImportError:
            pass
        return self.EVENT_COLORS.get(marker.event_name, QColor(100, 100, 200))


class TimelineScene(QGraphicsScene):
    """Graphics scene managing timeline elements."""

    seek_requested = Signal(int)
    event_double_clicked = Signal(object)
    event_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QColor(AppColors.ELEMENT_BG))

        self.pixels_per_second = 10.0
        self.track_height = 28
        self.ruler_height = 40
        self.fps = 30.0

        self.tracks = []
        self.markers = []
        self.event_items = []

        self.current_time_line = None
        self.current_time_marker = None
        self.ruler_items = []
        self.track_background_items = []
        self.track_header_items = []

        # FIX: Guard against re-entrant rebuild
        self._is_rebuilding = False

    def set_tracks(self, track_names: List[str]):
        self.tracks = list(track_names)
        self._safe_rebuild()

    def set_markers(self, markers: List[Marker]):
        # FIX: Defensive copy — prevents crash if original list
        # is mutated while we iterate during rebuild
        self.markers = list(markers)
        self._safe_rebuild()

    def add_event(self, track_name: str, start_sec: float, duration_sec: float,
                  label: str = "", color: QColor = None):
        marker = Marker(
            id=0,
            start_frame=int(start_sec * self.fps),
            end_frame=int((start_sec + duration_sec) * self.fps),
            event_name=track_name,
            note=label
        )
        if color:
            marker._display_color = color
        self.markers.append(marker)
        self._draw_single_event(marker)

    def set_duration(self, total_seconds: float):
        w = total_seconds * self.pixels_per_second + 200
        h = len(self.tracks) * self.track_height + self.ruler_height + 20
        self.setSceneRect(0, 0, w, h)

    def _safe_rebuild(self) -> None:
        """Rebuild with re-entrance guard."""
        if self._is_rebuilding:
            return
        self._is_rebuilding = True
        try:
            self._do_rebuild()
        except Exception as e:
            print(f"Timeline scene rebuild error: {e}")
        finally:
            self._is_rebuilding = False

    def rebuild(self):
        """Public rebuild — delegates to guarded version."""
        self._safe_rebuild()

    def _do_rebuild(self):
        """Actual rebuild logic (called only from _safe_rebuild)."""
        self.clear()

        self.event_items = []
        self.ruler_items = []
        self.track_background_items = []
        self.track_header_items = []
        self.current_time_line = None
        self.current_time_marker = None

        self._draw_tracks()
        self._draw_ruler()
        self._draw_events()
        self._draw_current_time_line()

    def _draw_tracks(self):
        for i, track_name in enumerate(self.tracks):
            y = self.ruler_height + i * self.track_height

            bg = QGraphicsRectItem(0, y, self.sceneRect().width(), self.track_height - 1)
            bg.setBrush(QColor(36, 36, 36) if i % 2 == 0 else QColor(32, 32, 32))
            bg.setPen(QPen(Qt.NoPen))
            self.addItem(bg)
            self.track_background_items.append(bg)

            if "Гол" in track_name:
                header_bg = QGraphicsRectItem(0, y, 140, self.track_height - 1)
                header_bg.setBrush(QColor(180, 140, 0, 180))
                header_bg.setPen(QPen(Qt.NoPen))
                self.addItem(header_bg)
                self.track_header_items.append(header_bg)

            text = QGraphicsTextItem(track_name, None)
            text.setDefaultTextColor(QColor(220, 220, 220))
            text.setFont(QFont("Segoe UI", 10))
            text.setPos(8, y + 4)
            self.addItem(text)

    def _draw_ruler(self):
        self.addRect(0, 0, self.sceneRect().width(), self.ruler_height,
                     QPen(Qt.NoPen), QBrush(QColor(AppColors.BACKGROUND)))

        font = QFont("Segoe UI", 9)
        total_sec = int(self.sceneRect().width() / self.pixels_per_second) + 1
        for sec in range(0, total_sec, 5):
            x = sec * self.pixels_per_second

            h = 12 if sec % 10 == 0 else 8
            tick = QGraphicsLineItem(x, self.ruler_height - h, x, self.ruler_height)
            tick.setPen(QPen(QColor(160, 160, 160), 1))
            self.addItem(tick)
            self.ruler_items.append(tick)

            if sec % 5 == 0:
                time_text = f"{sec // 60:02d}:{sec % 60:02d}"
                text_item = QGraphicsTextItem(time_text, None)
                text_item.setDefaultTextColor(QColor(200, 200, 200))
                text_item.setFont(font)
                text_item.setPos(x - 20, 12)
                self.addItem(text_item)
                self.ruler_items.append(text_item)

    def _draw_events(self):
        # FIX: iterate over snapshot, not live list
        for marker in self.markers:
            self._draw_single_event(marker)

    def _draw_single_event(self, marker: Marker):
        try:
            track_index = self.tracks.index(marker.event_name)
        except ValueError:
            return

        event_item = EventItem(marker, track_index, self.pixels_per_second,
                               self.track_height, self.ruler_height, self.fps)
        self.addItem(event_item)
        self.event_items.append(event_item)

    def _draw_current_time_line(self):
        self.current_time_line = QGraphicsLineItem(0, 0, 0, self.sceneRect().height())
        self.current_time_line.setPen(QPen(QColor(220, 30, 30), 1, Qt.DashLine))
        self.addItem(self.current_time_line)

        triangle = QGraphicsPolygonItem()
        triangle.setPolygon(QPolygonF([
            QPointF(-4, self.ruler_height),
            QPointF(4, self.ruler_height),
            QPointF(0, self.ruler_height + 8)
        ]))
        triangle.setBrush(QBrush(QColor(255, 255, 0)))
        triangle.setPen(QPen(Qt.NoPen))
        self.addItem(triangle)
        self.current_time_marker = triangle

    def set_current_time(self, seconds: float):
        if self._is_rebuilding:
            return
        if self.current_time_line:
            x = seconds * self.pixels_per_second
            self.current_time_line.setLine(x, 0, x, self.sceneRect().height())
            if self.current_time_marker:
                self.current_time_marker.setPos(x, 0)

    def set_fps(self, fps: float):
        self.fps = fps

    def get_pixels_per_second(self) -> float:
        return self.pixels_per_second

    def set_zoom(self, pixels_per_second: float):
        self.pixels_per_second = max(5.0, min(20.0, pixels_per_second))
        self._safe_rebuild()


class TimelineWidget(QGraphicsView):
    """Graphics view widget for the timeline."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.scene = TimelineScene(self)
        self.setScene(self.scene)

        self.scene.seek_requested.connect(self._on_seek_requested)

    def init_tracks(self, track_names: List[str], total_frames: int, fps: float = 30.0):
        self.scene.set_fps(fps)
        self.scene.set_tracks(track_names)
        total_sec = total_frames / fps
        self.scene.set_duration(total_sec)

    def set_markers(self, markers: List[Marker]):
        self.scene.set_markers(markers)

    def set_current_frame(self, frame: int, fps: float = 30.0):
        sec = frame / fps
        self.scene.set_current_time(sec)

    def set_zoom(self, pixels_per_second: float):
        self.scene.set_zoom(pixels_per_second)

    def rebuild(self, animate_new: bool = True):
        self.scene.rebuild()

    def set_total_frames(self, total_frames: int):
        total_sec = total_frames / self.scene.fps
        self.scene.set_duration(total_sec)

    def set_fps(self, fps: float):
        self.scene.set_fps(fps)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            zoom_factor = 1.25 if event.angleDelta().y() > 0 else 0.8
            old_zoom = self.scene.pixels_per_second
            self.set_zoom(old_zoom * zoom_factor)
            mouse_pos = self.mapToScene(event.pos())
            self.centerOn(mouse_pos)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            if scene_pos.y() <= self.scene.ruler_height:
                frame = int(scene_pos.x() / self.scene.pixels_per_second * self.scene.fps)
                frame = max(0, frame)
                self.scene.seek_requested.emit(frame)
        super().mousePressEvent(event)

    def _on_seek_requested(self, frame: int):
        pass