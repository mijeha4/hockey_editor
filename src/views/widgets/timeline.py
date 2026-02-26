"""
Timeline Widget - professional timeline graphics with zoom controls.
"""

from __future__ import annotations

from typing import List, Optional, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsLineItem, QGraphicsRectItem, QGraphicsTextItem, QScrollArea,
    QGraphicsItem, QGraphicsSceneMouseEvent, QMenu, QPushButton, QLabel,
)
from PySide6.QtCore import Qt, QRectF, Signal, QPointF, QTimer
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter, QFontMetrics

from services.events.custom_event_manager import get_custom_event_manager
from models.domain.marker import Marker


# ──────────────────────────────────────────────────────────────────────────────
# Zoom constants
# ──────────────────────────────────────────────────────────────────────────────

ZOOM_MIN = 0.001      # px/frame — 2h видео ≈ 650px
ZOOM_MAX = 20.0       # px/frame — максимальная детализация
ZOOM_DEFAULT = 0.8    # px/frame — значение по умолчанию
ZOOM_FACTOR = 1.3     # множитель при одном шаге колёсика

# Варианты шага времени (в секундах) для ruler/grid
TIME_STEPS = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600]


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
        self.original_idx: int = -1
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

        painter.save()
        painter.setClipRect(rect)

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

        avail = rect.width() - 8
        if avail >= 12:
            painter.setPen(QPen(Qt.white))
            font = QFont("Segoe UI", 9)
            painter.setFont(font)

            text = self._display_text()
            fm = QFontMetrics(font)
            if fm.horizontalAdvance(text) > avail:
                text = fm.elidedText(text, Qt.ElideRight, int(avail))

            x = rect.left() + 4
            y = rect.center().y() + fm.ascent() / 2
            painter.drawText(int(x), int(y), text)

        painter.restore()

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

    context_edit_requested = Signal(int)
    context_delete_requested = Signal(int)
    context_duplicate_requested = Signal(int)
    context_jump_requested = Signal(int)
    context_export_requested = Signal(int)

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller

        self.pixels_per_frame = ZOOM_DEFAULT
        self.track_height = 45
        self.header_width = 150
        self.ruler_height = 30

        self._markers: List[Marker] = []
        self._total_frames: int = 0
        self._fps: float = 30.0

        self._marker_to_original_idx: Dict[int, int] = {}

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

    def set_marker_index_map(self, index_map: Dict[int, int]) -> None:
        self._marker_to_original_idx = dict(index_map)

    def get_original_idx_for_marker(self, marker: Marker) -> int:
        return self._marker_to_original_idx.get(marker.id, -1)

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

    # ─── Zoom helpers ────────────────────────────────────────────────

    def _calc_time_step(self, min_spacing_px: float) -> int:
        """Вычислить оптимальный шаг времени (в секундах) для текущего масштаба.

        Подбирает из TIME_STEPS первый интервал, при котором расстояние
        между метками >= min_spacing_px пикселей.
        """
        fps = self.get_fps()
        pps = self.pixels_per_frame * fps  # пикселей на секунду

        if pps <= 0:
            return 3600

        for step in TIME_STEPS:
            if step * pps >= min_spacing_px:
                return step
        return 3600  # fallback: 1 час

    def _format_ruler_time(self, seconds: int) -> str:
        """Форматировать секунды для линейки.

        Автоматически выбирает формат:
        - MM:SS  для видео < 1 часа
        - H:MM:SS для видео >= 1 часа
        """
        total_sec = self.get_total_frames() / self.get_fps()
        show_hours = total_sec >= 3600

        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60

        if show_hours or h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    # ─── Mouse events ───────────────────────────────────────────────

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        scene_pos = event.scenePos()

        if scene_pos.y() <= self.ruler_height:
            frame = int((scene_pos.x() - self.header_width) / self.pixels_per_frame)
            frame = max(0, frame)
            self.seek_requested.emit(frame)
            event.accept()
            return

        clicked_items = self.items(scene_pos)
        for item in clicked_items:
            if isinstance(item, SegmentGraphicsItem):
                self.event_selected.emit(item.marker)
                event.accept()
                return

        if scene_pos.x() > self.header_width:
            frame = int((scene_pos.x() - self.header_width) / self.pixels_per_frame)
            frame = max(0, frame)
            self.seek_requested.emit(frame)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
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

    def contextMenuEvent(self, event) -> None:
        scene_pos = event.scenePos()
        clicked_items = self.items(scene_pos)

        segment_item: Optional[SegmentGraphicsItem] = None
        for item in clicked_items:
            if isinstance(item, SegmentGraphicsItem):
                segment_item = item
                break

        if segment_item is None:
            super().contextMenuEvent(event)
            return

        marker = segment_item.marker
        original_idx = self.get_original_idx_for_marker(marker)

        if original_idx < 0:
            original_idx = getattr(segment_item, 'original_idx', -1)

        if original_idx < 0:
            super().contextMenuEvent(event)
            return

        event_mgr = get_custom_event_manager()
        evt = event_mgr.get_event(marker.event_name)
        event_display_name = evt.get_localized_name() if evt else marker.event_name

        fps = self.get_fps()
        start_time = self._format_time(marker.start_frame / fps) if fps > 0 else "??:??"
        end_time = self._format_time(marker.end_frame / fps) if fps > 0 else "??:??"
        duration = self._format_time((marker.end_frame - marker.start_frame) / fps) if fps > 0 else "??:??"

        menu = QMenu()
        menu.setStyleSheet(self._get_context_menu_style())

        header_action = menu.addAction(f"📌 {event_display_name}")
        header_action.setEnabled(False)
        time_action = menu.addAction(f"⏱ {start_time} → {end_time} ({duration})")
        time_action.setEnabled(False)

        menu.addSeparator()

        jump_action = menu.addAction("▶ Перейти к началу")
        edit_action = menu.addAction("✏️ Редактировать")
        duplicate_action = menu.addAction("📋 Дублировать")

        menu.addSeparator()

        export_action = menu.addAction("📤 Экспортировать клип")

        menu.addSeparator()

        delete_action = menu.addAction("🗑️ Удалить")
        delete_action.setObjectName("delete_action")

        chosen = menu.exec(event.screenPos())

        if chosen == jump_action:
            self.context_jump_requested.emit(original_idx)
        elif chosen == edit_action:
            self.context_edit_requested.emit(original_idx)
        elif chosen == duplicate_action:
            self.context_duplicate_requested.emit(original_idx)
        elif chosen == export_action:
            self.context_export_requested.emit(original_idx)
        elif chosen == delete_action:
            self.context_delete_requested.emit(original_idx)

        event.accept()

    @staticmethod
    def _format_time(seconds: float) -> str:
        if seconds < 0:
            seconds = 0
        total = int(seconds)
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    @staticmethod
    def _get_context_menu_style() -> str:
        return """
            QMenu {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 4px 0px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                margin: 1px 4px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: #1a4d7a;
                color: #ffffff;
            }
            QMenu::item:disabled {
                color: #888888;
            }
            QMenu::separator {
                height: 1px;
                background-color: #444444;
                margin: 4px 8px;
            }
            QMenu::item#delete_action:selected {
                background-color: #8b0000;
            }
        """

    # ─── Drawing ─────────────────────────────────────────────────────

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

        # ── Grid lines ──
        fps = self.get_fps()
        if fps <= 0:
            return

        grid_pen = QPen(QColor("#333333"), 1)
        painter.setPen(grid_pen)

        start_frame = max(0, int((rect.left() - self.header_width) / self.pixels_per_frame))
        end_frame = int((rect.right() - self.header_width) / self.pixels_per_frame) + 1

        step_seconds = self._calc_time_step(60)

        start_sec = start_frame / fps
        end_sec = end_frame / fps
        first_sec = int(start_sec // step_seconds) * step_seconds

        sec = first_sec
        while sec <= end_sec:
            frame = int(sec * fps)
            x = frame * self.pixels_per_frame + self.header_width
            if rect.left() <= x <= rect.right():
                painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
            sec += step_seconds

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)

        # ── Ruler background ──
        ruler_rect = QRectF(rect.left(), 0, rect.width(), self.ruler_height)
        painter.fillRect(ruler_rect, QColor("#1a1a1a"))

        fps = self.get_fps()
        if fps <= 0:
            return

        start_frame = max(0, int((rect.left() - self.header_width) / self.pixels_per_frame))
        end_frame = int((rect.right() - self.header_width) / self.pixels_per_frame) + 1

        step_seconds = self._calc_time_step(80)

        start_sec = start_frame / fps
        end_sec = end_frame / fps
        first_sec = int(start_sec // step_seconds) * step_seconds

        font = QFont("Segoe UI", 8)
        fm = QFontMetrics(font)
        painter.setFont(font)

        last_text_x = float("-inf")
        sec = first_sec

        while sec <= end_sec:
            frame = int(sec * fps)
            x = frame * self.pixels_per_frame + self.header_width

            if rect.left() <= x <= rect.right():
                # Tick
                painter.setPen(QPen(QColor("#666666"), 1))
                painter.drawLine(int(x), self.ruler_height - 5, int(x), self.ruler_height)

                # Label
                text = self._format_ruler_time(int(sec))
                text_w = fm.horizontalAdvance(text)
                text_x = x - text_w // 2

                if text_x >= last_text_x + 5:
                    painter.setPen(QPen(Qt.white))
                    painter.drawText(int(text_x), 20, text)
                    last_text_x = text_x + text_w

            sec += step_seconds

    # ─── Rebuild ─────────────────────────────────────────────────────

    def rebuild(self, animate_new: bool = False) -> None:
        if getattr(self, '_is_rebuilding', False):
            return
        self._is_rebuilding = True
        try:
            self._rebuild_internal(animate_new)
        finally:
            self._is_rebuilding = False

    def _rebuild_internal(self, animate_new: bool = False) -> None:
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

        content_w = total_frames * self.pixels_per_frame + self.header_width + 150

        # Сцена не уже viewport (чтобы фон заполнял всё)
        view_width = 0
        for v in self.views():
            vw = v.viewport().width()
            if vw > view_width:
                view_width = vw
        scene_w = max(content_w, view_width)

        scene_h = len(events) * self.track_height + self.ruler_height + 50
        self.setSceneRect(0, 0, scene_w, scene_h)

        end_x = (total_frames - 1) * self.pixels_per_frame + self.header_width
        self.video_end_line.setLine(end_x, 0, end_x, scene_h)
        self.video_end_label.setPos(end_x - 35, -5)

        track_index: Dict[str, int] = {e.name: i for i, e in enumerate(events)}

        header_font = QFont("Segoe UI", 10, QFont.Bold)
        header_fm = QFontMetrics(header_font)
        max_header_text_w = self.header_width - 20

        for e in events:
            i = track_index[e.name]
            y = i * self.track_height + self.ruler_height

            bg = QGraphicsRectItem(0, y, self.header_width, self.track_height)
            bg._is_header_bg = True
            bg.setPen(Qt.NoPen)
            bg.setBrush(QBrush(QColor("#2a2a2a")))
            bg.setZValue(10)
            self.addItem(bg)

            elided_name = header_fm.elidedText(
                e.get_localized_name(), Qt.ElideRight, max_header_text_w
            )
            text_item = QGraphicsTextItem(elided_name)
            text_item.setDefaultTextColor(QColor(Qt.white))
            text_item.setFont(header_font)
            text_item.setPos(10, y + 10)
            text_item.setZValue(11)
            self.addItem(text_item)

        for marker in self._markers:
            i = track_index.get(marker.event_name)
            if i is None:
                continue
            y = i * self.track_height + self.ruler_height
            x = marker.start_frame * self.pixels_per_frame + self.header_width
            w = max(4.0, (marker.end_frame - marker.start_frame) * self.pixels_per_frame)

            seg = SegmentGraphicsItem(marker)
            seg.original_idx = self._marker_to_original_idx.get(marker.id, -1)
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

    context_edit_requested = Signal(int)
    context_delete_requested = Signal(int)
    context_duplicate_requested = Signal(int)
    context_jump_requested = Signal(int)
    context_export_requested = Signal(int)

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ══════════════════════════════════════════════════════════════
        # Панель масштабирования
        # ══════════════════════════════════════════════════════════════
        zoom_bar = QWidget()
        zoom_bar.setFixedHeight(28)
        zoom_bar.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #333;")
        zoom_layout = QHBoxLayout(zoom_bar)
        zoom_layout.setContentsMargins(6, 2, 6, 2)
        zoom_layout.setSpacing(4)

        btn_style = """
            QPushButton {
                background-color: #2a2a2a; color: #ccc;
                border: 1px solid #444; border-radius: 3px;
                padding: 1px 8px; font-size: 13px;
                min-width: 26px; max-height: 22px;
            }
            QPushButton:hover { background-color: #3a3a3a; color: #fff; }
            QPushButton:pressed { background-color: #1a1a1a; }
        """

        self._zoom_out_btn = QPushButton("−")
        self._zoom_out_btn.setToolTip("Уменьшить масштаб (Ctrl+Колесо)")
        self._zoom_out_btn.setStyleSheet(btn_style)
        self._zoom_out_btn.clicked.connect(self._zoom_out)
        zoom_layout.addWidget(self._zoom_out_btn)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setToolTip("Увеличить масштаб (Ctrl+Колесо)")
        self._zoom_in_btn.setStyleSheet(btn_style)
        self._zoom_in_btn.clicked.connect(self._zoom_in)
        zoom_layout.addWidget(self._zoom_in_btn)

        self._fit_btn = QPushButton("⊞ Вместить всё")
        self._fit_btn.setToolTip("Уместить всю длину видео в ширину экрана")
        self._fit_btn.setStyleSheet(btn_style.replace("min-width: 26px", "min-width: 80px"))
        self._fit_btn.clicked.connect(self.fit_to_view)
        zoom_layout.addWidget(self._fit_btn)

        zoom_layout.addSpacing(12)

        self._zoom_label = QLabel("")
        self._zoom_label.setStyleSheet("color: #888; font-size: 10px;")
        zoom_layout.addWidget(self._zoom_label)

        zoom_layout.addStretch()
        layout.addWidget(zoom_bar)

        # ══════════════════════════════════════════════════════════════
        # Таймлайн
        # ══════════════════════════════════════════════════════════════
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
        layout.addWidget(scroll, 1)

        # Проброс сигналов
        self.scene.seek_requested.connect(self.seek_requested)
        self.scene.event_selected.connect(self.event_selected)
        self.scene.event_double_clicked.connect(self.event_double_clicked)
        self.scene.context_edit_requested.connect(self.context_edit_requested)
        self.scene.context_delete_requested.connect(self.context_delete_requested)
        self.scene.context_duplicate_requested.connect(self.context_duplicate_requested)
        self.scene.context_jump_requested.connect(self.context_jump_requested)
        self.scene.context_export_requested.connect(self.context_export_requested)

        self._markers: List[Marker] = []
        self._connect_controller_signals(controller)
        get_custom_event_manager().events_changed.connect(lambda: self.rebuild(False))

        # Обновить label после первого показа
        QTimer.singleShot(100, self._update_zoom_label)

    # ─── Controller ──────────────────────────────────────────────────

    def _connect_controller_signals(self, controller) -> None:
        if not controller:
            return
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
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

    # ─── Markers ─────────────────────────────────────────────────────

    def set_markers(self, markers: List[Marker]) -> None:
        self._markers = list(markers)
        self.scene.set_markers(self._markers)
        self.rebuild(False)

    def set_markers_with_indices(self, markers: List[Marker], index_map: Dict[int, int]) -> None:
        self._markers = list(markers)
        self.scene.set_markers(self._markers)
        self.scene.set_marker_index_map(index_map)
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
            self._update_zoom_label()

    def set_current_frame(self, frame: int, fps: float) -> None:
        self.scene.update_playhead(frame)

    def init_tracks(self, track_names, total_frames, fps) -> None:
        self.rebuild(False)

    def _on_controller_markers_changed(self) -> None:
        if self.controller and getattr(self.controller, '_updating', False):
            return
        if self.controller:
            if hasattr(self.controller, "get_filtered_pairs"):
                pairs = self.controller.get_filtered_pairs()
                markers = [m for _, m in pairs]
                index_map = {m.id: idx for idx, m in pairs}
                self.scene.set_marker_index_map(index_map)
                self.scene.set_markers(markers)
                self.rebuild(False)
            elif hasattr(self.controller, "get_filtered_markers"):
                self.set_markers(self.controller.get_filtered_markers())
            else:
                self.set_markers(self.controller.markers)

    # ─── Zoom ────────────────────────────────────────────────────────

    def fit_to_view(self) -> None:
        """Уместить всю длину видео в видимую ширину."""
        total_frames = self.scene.get_total_frames()
        if total_frames <= 1:
            return

        available = self.view.viewport().width() - self.scene.header_width - 50
        if available <= 100:
            available = 800

        optimal_ppf = available / total_frames
        self.scene.pixels_per_frame = max(ZOOM_MIN, min(ZOOM_MAX, optimal_ppf))
        self.rebuild(False)
        self.view.horizontalScrollBar().setValue(0)

    def _zoom_in(self) -> None:
        self._apply_zoom(ZOOM_FACTOR)

    def _zoom_out(self) -> None:
        self._apply_zoom(1.0 / ZOOM_FACTOR)

    def _apply_zoom(self, factor: float, center_frame: Optional[int] = None) -> None:
        old_ppf = self.scene.pixels_per_frame
        new_ppf = max(ZOOM_MIN, min(ZOOM_MAX, old_ppf * factor))

        if new_ppf == old_ppf:
            return

        self.scene.pixels_per_frame = new_ppf
        self.rebuild(False)

        # Центрировать на текущем кадре или на центре видимой области
        if center_frame is None and self.controller:
            center_frame = self.controller.get_current_frame_idx()
        if center_frame is not None and center_frame >= 0:
            x = center_frame * new_ppf + self.scene.header_width
            self.view.horizontalScrollBar().setValue(
                int(x - self.view.viewport().width() // 2)
            )

    def _update_zoom_label(self) -> None:
        """Обновить метку с информацией о масштабе."""
        fps = self.scene.get_fps()
        total_frames = self.scene.get_total_frames()
        ppf = self.scene.pixels_per_frame

        if fps <= 0 or total_frames <= 1:
            self._zoom_label.setText("")
            return

        # Сколько секунд помещается в видимую область
        viewport_w = self.view.viewport().width() - self.scene.header_width
        if viewport_w <= 0:
            viewport_w = 100
        visible_frames = viewport_w / ppf
        visible_sec = visible_frames / fps

        total_sec = total_frames / fps

        # Процент масштаба (100% = вся длина видео помещается точно)
        ideal_ppf = viewport_w / total_frames
        zoom_pct = int((ppf / ideal_ppf) * 100) if ideal_ppf > 0 else 100

        self._zoom_label.setText(
            f"Масштаб: {zoom_pct}%  |  "
            f"Видимо: {self._format_duration(visible_sec)} "
            f"из {self._format_duration(total_sec)}"
        )

    @staticmethod
    def _format_duration(seconds: float) -> str:
        seconds = max(0, int(seconds))
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    # ─── Events ──────────────────────────────────────────────────────

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = ZOOM_FACTOR if event.angleDelta().y() > 0 else (1.0 / ZOOM_FACTOR)

            # Определить кадр под курсором для центрирования
            scene_pos = self.view.mapToScene(self.view.mapFromGlobal(event.globalPosition().toPoint()))
            center_frame = int((scene_pos.x() - self.scene.header_width) / self.scene.pixels_per_frame)
            center_frame = max(0, center_frame)

            self._apply_zoom(factor, center_frame)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        super().contextMenuEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_zoom_label()