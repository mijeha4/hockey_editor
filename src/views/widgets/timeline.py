"""
Timeline Widget - professional timeline graphics.
"""

from __future__ import annotations

from typing import List, Optional, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsLineItem,
    QGraphicsRectItem, QGraphicsTextItem, QScrollArea, QGraphicsItem,
    QGraphicsSceneMouseEvent
)
from PySide6.QtCore import Qt, QRectF, Signal, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter, QFontMetrics

from services.events.custom_event_manager import get_custom_event_manager
from models.domain.marker import Marker


# ──────────────────────────────────────────────────────────────────────────────
# Helpers: view / scroll
# ──────────────────────────────────────────────────────────────────────────────

class TimelineGraphicsView(QGraphicsView):
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            event.ignore()
        else:
            super().wheelEvent(event)


class TimelineScrollArea(QScrollArea):
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            event.ignore()
        else:
            super().wheelEvent(event)


# ──────────────────────────────────────────────────────────────────────────────
# Segment item
# ──────────────────────────────────────────────────────────────────────────────

class SegmentGraphicsItem(QGraphicsRectItem):
    def __init__(self, marker: Marker):
        super().__init__()
        self.marker = marker
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        event = get_custom_event_manager().get_event(marker.event_name)
        self.event_color = QColor(event.color) if event else QColor("#888888")
        self.is_hovered = False
        self.setToolTip(self._full_tooltip())

    def _display_text(self) -> str:
        note = (self.marker.note or "").strip()
        if note:
            return note
        event = get_custom_event_manager().get_event(self.marker.event_name)
        return event.get_localized_name() if event else self.marker.event_name

    def _full_tooltip(self) -> str:
        event = get_custom_event_manager().get_event(self.marker.event_name)
        event_name = event.get_localized_name() if event else self.marker.event_name
        note = (self.marker.note or "").strip()
        return f"{note}\n({event_name})" if note else event_name

    def paint(self, painter, option, widget):
        rect = self.rect()
        fill = QColor(self.event_color)
        if self.is_hovered:
            fill = fill.lighter(120)
        fill.setAlpha(200)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(fill))
        painter.drawRoundedRect(rect, 4, 4)

        if self.isSelected():
            pen = QPen(QColor(Qt.white), 2, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 3, 3)

        painter.setPen(QPen(Qt.white))
        font = QFont("Segoe UI", 9)
        painter.setFont(font)

        text = self._display_text()
        fm = QFontMetrics(font)
        avail = rect.width() - 8
        if fm.horizontalAdvance(text) > avail:
            text = fm.elidedText(text, Qt.ElideRight, int(avail))

        x = rect.left() + 4
        y = rect.center().y() + fm.ascent() / 2
        painter.drawText(int(x), int(y), text)

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)


# ──────────────────────────────────────────────────────────────────────────────
# Scene
# ──────────────────────────────────────────────────────────────────────────────

class TimelineGraphicsScene(QGraphicsScene):
    seek_requested = Signal(int)
    event_selected = Signal(Marker)
    event_double_clicked = Signal(Marker)

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller

        self.pixels_per_frame = 0.8
        self.track_height = 45
        self.header_width = 150
        self.ruler_height = 30

        self._markers: List[Marker] = []
        self._total_frames: int = 0
        self._fps: float = 30.0

        self.playhead = QGraphicsLineItem()
        self.playhead.setPen(QPen(QColor("#FFFF00"), 3, Qt.SolidLine, Qt.RoundCap))
        self.playhead.setZValue(1000)
        self.addItem(self.playhead)

        self.video_end_line = QGraphicsLineItem()
        self.video_end_line.setPen(QPen(QColor("#FF0000"), 2, Qt.SolidLine, Qt.RoundCap))
        self.video_end_line.setZValue(900)
        self.addItem(self.video_end_line)

        self.video_end_label = QGraphicsTextItem("Конец видео")
        self.video_end_label.setDefaultTextColor(QColor("#FF0000"))
        self.video_end_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.video_end_label.setZValue(900)
        self.addItem(self.video_end_label)

    def set_markers(self, markers: List[Marker]) -> None:
        self._markers = list(markers)

    def get_total_frames(self) -> int:
        if self.controller and hasattr(self.controller, 'get_total_frames'):
            return max(self.controller.get_total_frames(), 1)
        return max(self._total_frames, 1)

    def get_fps(self) -> float:
        if self.controller and hasattr(self.controller, 'get_fps'):
            fps = self.controller.get_fps()
            if fps > 0:
                return fps
        return self._fps if self._fps > 0 else 30.0

    # ──────────────────────────────────────────────────────────────────
    # FIX: Mouse event handling — без этого клики по таймлайну не работают
    # ──────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Клик по ruler → seek, клик по сегменту → select."""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        scene_pos = event.scenePos()

        # Клик на ruler (верхняя полоса) → перемотка
        if scene_pos.y() <= self.ruler_height:
            frame = int((scene_pos.x() - self.header_width) / self.pixels_per_frame)
            frame = max(0, frame)
            self.seek_requested.emit(frame)
            event.accept()
            return

        # Клик на сегмент → выделение
        clicked_items = self.items(scene_pos)
        for item in clicked_items:
            if isinstance(item, SegmentGraphicsItem):
                self.event_selected.emit(item.marker)
                event.accept()
                return

        # Клик на пустое место трека → перемотка
        if scene_pos.x() > self.header_width:
            frame = int((scene_pos.x() - self.header_width) / self.pixels_per_frame)
            frame = max(0, frame)
            self.seek_requested.emit(frame)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Двойной клик по сегменту → открыть редактор."""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return

        scene_pos = event.scenePos()
        clicked_items = self.items(scene_pos)
        for item in clicked_items:
            if isinstance(item, SegmentGraphicsItem):
                self.event_double_clicked.emit(item.marker)
                event.accept()
                return

        super().mouseDoubleClickEvent(event)

    # ──────────────────────────────────────────────────────────────────

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)

        events = get_custom_event_manager().get_all_events()
        if not events:
            return

        even = QColor("#1e1e1e")
        odd = QColor("#232323")

        for i in range(len(events)):
            y = i * self.track_height + self.ruler_height
            track_rect = QRectF(rect.left(), y, rect.width(), self.track_height)
            if track_rect.intersects(rect):
                painter.fillRect(track_rect, even if i % 2 == 0 else odd)

        fps = self.get_fps()
        if fps <= 0:
            return

        grid_pen = QPen(QColor("#333333"), 1)
        painter.setPen(grid_pen)

        start_frame = max(0, int((rect.left() - self.header_width) / self.pixels_per_frame))
        end_frame = int((rect.right() - self.header_width) / self.pixels_per_frame) + 1

        min_spacing_px = 60
        cur_spacing_px = self.pixels_per_frame * fps * 5

        if cur_spacing_px < min_spacing_px:
            step_seconds = max(5, int(min_spacing_px / (self.pixels_per_frame * fps)))
            if step_seconds <= 7: step_seconds = 5
            elif step_seconds <= 12: step_seconds = 10
            elif step_seconds <= 20: step_seconds = 15
            elif step_seconds <= 40: step_seconds = 30
            else: step_seconds = 60
        else:
            step_seconds = 5

        first_seconds = (start_frame // int(step_seconds * fps)) * step_seconds
        sec = first_seconds
        while True:
            frame = int(sec * fps)
            if frame > end_frame:
                break
            x = frame * self.pixels_per_frame + self.header_width
            if rect.left() <= x <= rect.right():
                painter.drawLine(x, rect.top(), x, rect.bottom())
            sec += step_seconds

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)

        ruler_rect = QRectF(rect.left(), 0, rect.width(), self.ruler_height)
        painter.fillRect(ruler_rect, QColor("#1a1a1a"))

        fps = self.get_fps()
        if fps <= 0:
            return

        start_frame = max(0, int((rect.left() - self.header_width) / self.pixels_per_frame))
        end_frame = int((rect.right() - self.header_width) / self.pixels_per_frame) + 1

        min_spacing_px = 80
        cur_spacing_px = self.pixels_per_frame * fps * 5

        if cur_spacing_px < min_spacing_px:
            step_seconds = max(5, int(min_spacing_px / (self.pixels_per_frame * fps)))
            if step_seconds <= 7: step_seconds = 5
            elif step_seconds <= 12: step_seconds = 10
            elif step_seconds <= 20: step_seconds = 15
            elif step_seconds <= 40: step_seconds = 30
            else: step_seconds = 60
        else:
            step_seconds = 5

        first_seconds = (start_frame // int(step_seconds * fps)) * step_seconds
        sec = first_seconds
        last_text_x = float("-inf")

        font = QFont("Segoe UI", 8)
        fm = QFontMetrics(font)
        painter.setFont(font)

        while True:
            frame = int(sec * fps)
            if frame > end_frame:
                break
            x = frame * self.pixels_per_frame + self.header_width
            if rect.left() <= x <= rect.right():
                painter.setPen(QPen(QColor("#666666"), 1))
                painter.drawLine(x, self.ruler_height - 5, x, self.ruler_height)

                minutes = sec // 60
                seconds = sec % 60
                text = f"{minutes:02d}:{seconds:02d}"
                text_w = fm.horizontalAdvance(text)
                text_x = x - text_w // 2

                if text_x >= last_text_x + 5:
                    painter.setPen(QPen(Qt.white))
                    painter.drawText(int(text_x), 20, text)
                    last_text_x = text_x + text_w
            sec += step_seconds

    def rebuild(self, animate_new: bool = False) -> None:
        total_frames = self.get_total_frames()
        events = get_custom_event_manager().get_all_events()
        if not events:
            return

        for item in list(self.items()):
            if item in (self.playhead, self.video_end_line, self.video_end_label):
                continue
            if isinstance(item, (SegmentGraphicsItem, QGraphicsTextItem)):
                self.removeItem(item)
            if isinstance(item, QGraphicsRectItem) and getattr(item, "_is_header_bg", False):
                self.removeItem(item)

        scene_w = total_frames * self.pixels_per_frame + self.header_width + 150
        scene_h = len(events) * self.track_height + self.ruler_height + 50
        self.setSceneRect(0, 0, scene_w, scene_h)

        end_x = (total_frames - 1) * self.pixels_per_frame + self.header_width
        self.video_end_line.setLine(end_x, 0, end_x, scene_h)
        self.video_end_label.setPos(end_x - 35, -5)

        track_index: Dict[str, int] = {e.name: i for i, e in enumerate(events)}

        for e in events:
            i = track_index[e.name]
            y = i * self.track_height + self.ruler_height

            bg = QGraphicsRectItem(0, y, self.header_width, self.track_height)
            bg._is_header_bg = True
            bg.setPen(Qt.NoPen)
            bg.setBrush(QBrush(QColor("#2a2a2a")))
            bg.setZValue(10)
            self.addItem(bg)

            text_item = QGraphicsTextItem(e.get_localized_name())
            text_item.setDefaultTextColor(QColor(Qt.white))
            text_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            text_item.setPos(10, y + 10)
            text_item.setZValue(11)
            self.addItem(text_item)

        for marker in self._markers:
            i = track_index.get(marker.event_name)
            if i is None:
                continue
            y = i * self.track_height + self.ruler_height
            x = marker.start_frame * self.pixels_per_frame + self.header_width
            w = max(10.0, (marker.end_frame - marker.start_frame) * self.pixels_per_frame)

            seg = SegmentGraphicsItem(marker)
            seg.setRect(x, y + 8, w, self.track_height - 16)
            seg.setZValue(100)
            self.addItem(seg)

        if self.controller:
            self.update_playhead(self.controller.get_current_frame_idx())

    def update_playhead(self, frame_idx: int) -> None:
        if frame_idx < 0:
            return
        x = frame_idx * self.pixels_per_frame + self.header_width
        self.playhead.setLine(x, 0.0, x, self.sceneRect().height())


# ──────────────────────────────────────────────────────────────────────────────
# Widget
# ──────────────────────────────────────────────────────────────────────────────

class TimelineWidget(QWidget):
    seek_requested = Signal(int)
    event_selected = Signal(Marker)
    event_double_clicked = Signal(Marker)

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view = TimelineGraphicsView()
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.scene = TimelineGraphicsScene(controller)
        self.view.setScene(self.scene)

        scroll = TimelineScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.view)
        layout.addWidget(scroll)

        self.scene.seek_requested.connect(self.seek_requested)
        self.scene.event_selected.connect(self.event_selected)
        self.scene.event_double_clicked.connect(self.event_double_clicked)

        self._markers: List[Marker] = []
        self._connect_controller_signals(controller)
        get_custom_event_manager().events_changed.connect(lambda: self.rebuild(False))

    def _connect_controller_signals(self, controller) -> None:
        if not controller:
            return
        try:
            controller.markers_changed.disconnect(self._on_controller_markers_changed)
        except (TypeError, RuntimeError):
            pass
        try:
            controller.playback_time_changed.disconnect(self.scene.update_playhead)
        except (TypeError, RuntimeError):
            pass
        controller.markers_changed.connect(self._on_controller_markers_changed)
        controller.playback_time_changed.connect(self.scene.update_playhead)

    def set_controller(self, controller) -> None:
        self.controller = controller
        self.scene.controller = controller
        self._connect_controller_signals(controller)
        self.rebuild(False)

    def set_markers(self, markers: List[Marker]) -> None:
        self._markers = list(markers)
        self.scene.set_markers(self._markers)
        self.rebuild(False)

    def set_total_frames(self, total_frames: int) -> None:
        self.scene._total_frames = max(0, total_frames)
        self.rebuild(False)

    def set_fps(self, fps: float) -> None:
        self.scene._fps = fps if fps > 0 else 30.0
        self.rebuild(False)

    def rebuild(self, animate_new: bool = False) -> None:
        if self.scene:
            self.scene.rebuild(animate_new)

    def set_current_frame(self, frame: int, fps: float) -> None:
        self.scene.update_playhead(frame)

    def init_tracks(self, track_names, total_frames, fps) -> None:
        self.rebuild(False)

    def _on_controller_markers_changed(self) -> None:
        if self.controller:
            self.set_markers(
                self.controller.get_filtered_markers()
                if hasattr(self.controller, "get_filtered_markers")
                else self.controller.markers
            )

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.25 if event.angleDelta().y() > 0 else 0.8
            self.scene.pixels_per_frame = max(0.1, min(10.0, self.scene.pixels_per_frame * factor))
            self.rebuild(False)
            if self.controller:
                x = self.controller.get_current_frame_idx() * self.scene.pixels_per_frame + self.scene.header_width
                self.view.horizontalScrollBar().setValue(int(x - self.view.width() // 2))
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        super().contextMenuEvent(event)