"""
Timeline Graphics - QGraphicsView-based professional timeline with interactive segments.
Поддерживает drag/resize отрезков, zoom, pan, context menu.
"""

from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QCursor
)
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsLineItem, QMenu
)
from typing import Optional, Dict, List
from ..utils.custom_events import get_custom_event_manager


class SegmentGraphicsItem(QGraphicsRectItem):
    """Интерактивный сегмент на таймлайне."""
    
    # Сигналы
    segment_moved = Signal(int, float, float)  # marker_idx, new_start_sec, new_end_sec
    segment_selected = Signal(int)  # marker_idx
    segment_double_clicked = Signal(int)  # marker_idx - for editing
    
    HANDLE_WIDTH = 8
    MIN_WIDTH = 10
    
    def __init__(self, marker_idx: int, start_x: float, end_x: float, 
                 track_y: float, track_height: float, color: QColor, fps: float,
                 marker_name: str = "", start_frame: int = 0, end_frame: int = 0):
        super().__init__(start_x, track_y + 5, end_x - start_x, track_height - 10)
        
        self.marker_idx = marker_idx
        self.track_height = track_height
        self.track_y = track_y
        self.fps = fps
        self.color = color
        self.marker_name = marker_name
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.is_selected = False
        self.drag_type = None  # "start", "end", "move"
        self.drag_start_x = 0
        self.drag_start_rect = None
        self.last_click_time = 0  # For double-click detection
        
        # Стиль
        self.setBrush(QBrush(QColor(255, 255, 255, 100)))
        self.setPen(QPen(color, 2))
        self.setAcceptHoverEvents(True)
        self.setZValue(1)
        
        # Текст маркера
        self.text_item = QGraphicsTextItem(f"Seg {marker_idx + 1}", self)
        self.text_item.setDefaultTextColor(QColor(255, 255, 255))
        self.text_item.setFont(QFont("Arial", 8))
        self.text_item.setPos(5, 5)

    def boundingRect(self):
        """Расширить область для удобства взаимодействия."""
        rect = super().boundingRect()
        return rect.adjusted(-self.HANDLE_WIDTH // 2, -2, self.HANDLE_WIDTH // 2, 2)

    def paint(self, painter, option, widget):
        """Отрисовка сегмента с ручками."""
        rect = self.rect()
        
        # Основная полоска
        painter.fillRect(rect, self.brush())
        painter.drawRect(rect)
        
        # Выделение
        if self.is_selected:
            painter.setPen(QPen(QColor(255, 255, 0), 3))
            painter.drawRect(rect.adjusted(-2, -2, 2, 2))
        
        # Ручки drag
        handle_color = QColor(255, 200, 0)
        painter.fillRect(rect.left() - self.HANDLE_WIDTH // 2, rect.top() + 5,
                        self.HANDLE_WIDTH, rect.height() - 10, handle_color)
        painter.fillRect(rect.right() - self.HANDLE_WIDTH // 2, rect.top() + 5,
                        self.HANDLE_WIDTH, rect.height() - 10, handle_color)

    def mousePressEvent(self, event):
        """Начало перетаскивания или double-click."""
        import time
        
        current_time = time.time()
        
        # Проверить double-click (< 300ms)
        if current_time - self.last_click_time < 0.3:
            self.segment_double_clicked.emit(self.marker_idx)
            self.last_click_time = 0
            return
        
        self.last_click_time = current_time
        
        self.is_selected = True
        self.segment_selected.emit(self.marker_idx)
        self.update()
        
        rect = self.rect()
        x = event.pos().x()
        
        # Определить тип перетаскивания
        if x < rect.left() + self.HANDLE_WIDTH:
            self.drag_type = "start"
        elif x > rect.right() - self.HANDLE_WIDTH:
            self.drag_type = "end"
        else:
            self.drag_type = "move"
        
        self.drag_start_x = x
        self.drag_start_rect = rect
        self.setCursor(QCursor(Qt.CursorShape.SizeHorCursor if self.drag_type != "move" else Qt.CursorShape.OpenHandCursor))

    def mouseMoveEvent(self, event):
        """Перетаскивание."""
        if self.drag_type is None:
            return
        
        delta_x = event.pos().x() - self.drag_start_x
        rect = self.rect()
        new_rect = self.drag_start_rect
        
        if self.drag_type == "start":
            new_left = self.drag_start_rect.left() + delta_x
            new_left = min(new_left, self.drag_start_rect.right() - self.MIN_WIDTH)
            new_rect.setLeft(new_left)
        elif self.drag_type == "end":
            new_right = self.drag_start_rect.right() + delta_x
            new_right = max(new_right, self.drag_start_rect.left() + self.MIN_WIDTH)
            new_rect.setRight(new_right)
        elif self.drag_type == "move":
            new_rect.translate(delta_x, 0)
        
        self.setRect(new_rect)

    def mouseReleaseEvent(self, event):
        """Конец перетаскивания - эмитировать сигнал."""
        if self.drag_type is None:
            return
        
        rect = self.rect()
        pixels_per_frame = self.scene().pixels_per_frame if hasattr(self.scene(), 'pixels_per_frame') else 1
        
        start_sec = rect.left() / pixels_per_frame / self.fps if self.fps > 0 else 0
        end_sec = rect.right() / pixels_per_frame / self.fps if self.fps > 0 else 0
        
        self.segment_moved.emit(self.marker_idx, start_sec, end_sec)
        self.drag_type = None

    def hoverEnterEvent(self, event):
        """Наведение курсора - показать tooltip."""
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        
        # Создать tooltip с информацией о сегменте
        start_time = self._format_time(self.start_frame / self.fps if self.fps > 0 else 0)
        end_time = self._format_time(self.end_frame / self.fps if self.fps > 0 else 0)
        duration = self.end_frame - self.start_frame
        duration_sec = duration / self.fps if self.fps > 0 else 0
        
        tooltip = (f"{self.marker_name}\n"
                  f"Time: {start_time} - {end_time}\n"
                  f"Duration: {duration} frames ({duration_sec:.2f}s)\n"
                  f"Double-click to edit")
        
        self.setToolTip(tooltip)

    def hoverLeaveEvent(self, event):
        """Уход курсора."""
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def deselect(self):
        """Отменить выделение."""
        self.is_selected = False
        self.update()
    
    def _format_time(self, seconds: float) -> str:
        """Форматировать время MM:SS."""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        return f"{minutes:02d}:{secs:02d}"


class PlayheadGraphicsItem(QGraphicsLineItem):
    """Индикатор текущей позиции воспроизведения."""
    
    def __init__(self, x: float, top_y: float, bottom_y: float):
        super().__init__(x, top_y, x, bottom_y)
        self.setPen(QPen(QColor(255, 255, 0), 2))
        self.setZValue(2)

    def update_position(self, x: float):
        """Обновить позицию playhead."""
        self.setLine(x, self.line().y1(), x, self.line().y2())


class TimelineGraphicsScene(QGraphicsScene):
    """QGraphicsScene для таймлайна с масштабированием."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixels_per_frame = 0.1  # Пиксели на один кадр
        self.track_height = 50
        self.header_height = 30
        self.fps = 30
        self.controller = None

        # CustomEventManager для получения цветов и событий
        self.event_manager = get_custom_event_manager()

        self.setBackgroundBrush(QBrush(QColor(26, 26, 26)))
        self.segment_items: Dict[int, SegmentGraphicsItem] = {}
        self.background_items: List = []  # ИСПРАВЛЕНО: список элементов фона для обновления

    def set_controller(self, controller):
        """Установить контроллер и обновить сцену."""
        self.controller = controller
        self.fps = controller.get_fps()
        self.update_scene()

    def update_scene(self):
        """Обновить все элементы сцены без пересоздания."""
        # ИСПРАВЛЕНО: НЕ очищать сцену, а обновлять существующие элементы
        if not self.controller:
            return

        self.fps = self.controller.get_fps()
        total_frames = self.controller.get_total_frames()

        # Размер сцены
        total_width = total_frames * self.pixels_per_frame
        total_height = self.header_height + len(self.event_manager.get_all_events()) * self.track_height
        self.setSceneRect(0, 0, total_width, total_height)

        # Отрисовать фон и сетку
        self._draw_background()

        # Отрисовать отрезки
        self._draw_segments()

        # Отрисовать playhead (если не существует)
        if not hasattr(self, 'playhead') or self.playhead is None:
            self._draw_playhead()

    def _clear_background_items(self):
        """Очистить элементы фона."""
        # ИСПРАВЛЕНО: удалить только элементы фона, не всю сцену
        for item in self.background_items:
            self.removeItem(item)
        self.background_items.clear()

    def _draw_background(self):
        """Отрисовать фон с временной сеткой."""
        # ИСПРАВЛЕНО: Очистить только фон и сетку перед перерисовкой
        self._clear_background_items()

        events = self.event_manager.get_all_events()

        # Заголовок
        header_rect = self.addRect(0, 0, self.sceneRect().width(), self.header_height)
        header_rect.setBrush(QBrush(QColor(35, 35, 35)))
        header_rect.setPen(QPen(QColor(100, 100, 100)))
        header_rect.setZValue(0)
        self.background_items.append(header_rect)

        # Дорожки для каждого события
        for idx, event in enumerate(events):
            track_y = self.header_height + idx * self.track_height

            # Фон дорожки
            track_rect = self.addRect(0, track_y, self.sceneRect().width(), self.track_height)
            bg_color = event.get_qcolor()
            bg_color.setAlpha(20)
            track_rect.setBrush(QBrush(bg_color))
            track_rect.setPen(QPen(QColor(80, 80, 80)))
            track_rect.setZValue(0)
            self.background_items.append(track_rect)

            # Метка дорожки
            label = self.addText(event.name)
            label.setDefaultTextColor(event.get_qcolor())
            label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            label.setPos(5, track_y + 15)
            label.setZValue(1)
            self.background_items.append(label)

        # Обновить высоту сцены
        total_height = self.header_height + len(events) * self.track_height
        self.setSceneRect(0, 0, self.sceneRect().width(), total_height)

        # Временная сетка
        self._draw_time_grid()

    def _draw_time_grid(self):
        """Отрисовать сетку с временными метками (каждую секунду)."""
        total_frames = self.controller.get_total_frames()
        fps = self.controller.get_fps()
        total_secs = total_frames / fps if fps > 0 else 0
        
        # Вертикальные линии каждую секунду
        for sec in range(0, int(total_secs) + 1):
            x = sec * fps * self.pixels_per_frame
            
            # Разные стили для каждых 5 секунд
            is_major = (sec % 5 == 0)
            pen_style = Qt.PenStyle.SolidLine if is_major else Qt.PenStyle.DotLine
            pen_width = 1 if is_major else 1
            pen_color = QColor(100, 100, 100) if is_major else QColor(60, 60, 60)
            
            # Вертикальная линия
            line = self.addLine(x, self.header_height, x, self.sceneRect().height())
            line.setPen(QPen(pen_color, pen_width, pen_style))
            line.setZValue(0)
            
            # Время (только для major lines)
            if is_major:
                time_text = self.addText(f"{sec}s")
                time_text.setDefaultTextColor(QColor(150, 150, 150))
                time_text.setFont(QFont("Arial", 8))
                time_text.setPos(x - 10, 5)
                time_text.setZValue(1)

    def _clear_segments(self):
        """Очистить сегменты."""
        # ИСПРАВЛЕНО: удалить только сегменты, сохранить playhead и фон
        for item in self.segment_items.values():
            self.removeItem(item)
        self.segment_items.clear()

    def _draw_segments(self):
        """Отрисовать отрезки."""
        # ИСПРАВЛЕНО: Очистить старые сегменты перед рисованием новых
        self._clear_segments()

        events = self.event_manager.get_all_events()
        events_dict = {event.name: (idx, event) for idx, event in enumerate(events)}

        for marker_idx, marker in enumerate(self.controller.markers):
            event_name = marker.event_name
            if event_name in events_dict:
                track_idx, event = events_dict[event_name]
                track_y = self.header_height + track_idx * self.track_height

                start_x = marker.start_frame * self.pixels_per_frame
                end_x = marker.end_frame * self.pixels_per_frame

                segment = SegmentGraphicsItem(
                    marker_idx,
                    start_x, end_x,
                    track_y, self.track_height,
                    event.get_qcolor(),
                    self.fps,
                    marker.event_name,
                    marker.start_frame,
                    marker.end_frame
                )

                segment.segment_moved.connect(self._on_segment_moved)
                segment.segment_selected.connect(self._on_segment_selected)
                segment.segment_double_clicked.connect(self._on_segment_double_clicked)

                self.addItem(segment)
                self.segment_items[marker_idx] = segment

    def _draw_playhead(self):
        """Отрисовать playhead."""
        current_frame = self.controller.get_current_frame_idx()
        x = current_frame * self.pixels_per_frame
        
        playhead = PlayheadGraphicsItem(
            x, self.header_height,
            self.sceneRect().height()
        )
        self.addItem(playhead)
        self.playhead = playhead

    def update_playhead(self, frame_idx: int):
        """Обновить позицию playhead."""
        if hasattr(self, 'playhead'):
            x = frame_idx * self.pixels_per_frame
            self.playhead.update_position(x)

    def _on_segment_moved(self, marker_idx: int, start_sec: float, end_sec: float):
        """Обработка перемещения сегмента."""
        fps = self.controller.get_fps()
        if fps > 0:
            self.controller.markers[marker_idx].start_frame = int(start_sec * fps)
            self.controller.markers[marker_idx].end_frame = int(end_sec * fps)
            self.controller.markers_changed.emit()

    def _on_segment_selected(self, marker_idx: int):
        """Обработка выделения сегмента."""
        for item in self.segment_items.values():
            if item.marker_idx != marker_idx:
                item.deselect()
    
    def _on_segment_double_clicked(self, marker_idx: int):
        """Обработка двойного клика - открыть редактор."""
        if hasattr(self, 'parent_view') and self.parent_view:
            self.parent_view.open_segment_editor(marker_idx)

    def set_zoom(self, factor: float):
        """Установить масштаб."""
        self.pixels_per_frame *= factor
        self.update_scene()


class TimelineGraphicsView(QGraphicsView):
    """QGraphicsView для отображения таймлайна с поддержкой масштабирования."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene_obj = TimelineGraphicsScene(self)
        self.scene_obj.parent_view = self  # Set reference for double-click
        self.setScene(self.scene_obj)
        
        self.setStyleSheet("background-color: #1a1a1a; border: none;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setMinimumHeight(200)
        self.main_window = None  # Will be set by MainWindow

    def set_controller(self, controller):
        """Установить контроллер."""
        self.scene_obj.set_controller(controller)
    
    def open_segment_editor(self, marker_idx: int):
        """Открыть редактор сегмента."""
        if self.main_window:
            self.main_window.open_segment_editor(marker_idx)

    def wheelEvent(self, event):
        """Масштабирование Ctrl+Wheel."""
        if event.modifiers() != Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(event)
            return
        
        factor = 1.2 if event.angleDelta().y() > 0 else 0.8
        self.scene_obj.set_zoom(factor)

    def mousePressEvent(self, event):
        """Клик на таймлайн для seek."""
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            
            # Клик ниже заголовка = seek
            if scene_pos.y() >= self.scene_obj.header_height:
                frame_idx = int(scene_pos.x() / self.scene_obj.pixels_per_frame)
                if self.scene_obj.controller:
                    self.scene_obj.controller.seek_frame(frame_idx)
        
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        """Контекстное меню для опций таймлайна."""
        menu = QMenu(self)
        zoom_in = menu.addAction("Zoom In (Ctrl+Scroll)")
        zoom_out = menu.addAction("Zoom Out (Ctrl+Scroll)")
        
        action = menu.exec(event.globalPos())
        if action == zoom_in:
            self.scene_obj.set_zoom(1.2)
        elif action == zoom_out:
            self.scene_obj.set_zoom(0.8)
