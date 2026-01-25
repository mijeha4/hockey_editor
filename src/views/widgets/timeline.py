"""
Timeline Widget - Recreated from hockey_editor_OLD/ui/timeline_graphics.py

Interactive timeline view for video editing with professional graphics.
Displays video timeline with segments, ruler, playhead, and track headers.
Supports zooming, seeking, and segment editing functionality.
Adapted to new MVC architecture.
"""

from typing import List, Optional
from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsScene, QGraphicsView, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsObject, QScrollArea, QWidget, QVBoxLayout, QMenu, QGraphicsItem
)
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter, QAction, QFontMetrics

# MVC imports
from services.events.custom_event_manager import get_custom_event_manager
from models.domain.marker import Marker


class TimelineGraphicsView(QGraphicsView):
    """Кастомный QGraphicsView, который игнорирует колесо мыши при Ctrl."""

    def wheelEvent(self, event):
        """Игнорировать колесо мыши при нажатом Ctrl, передавая родителю."""
        if event.modifiers() & Qt.ControlModifier:
            # При Ctrl игнорируем, передаем родителю для масштабирования
            event.ignore()
        else:
            # Без Ctrl обычная обработка
            super().wheelEvent(event)


class TimelineScrollArea(QScrollArea):
    """Кастомный QScrollArea, который игнорирует колесо мыши при Ctrl для масштабирования."""

    def wheelEvent(self, event):
        """Игнорировать колесо мыши при нажатом Ctrl, чтобы позволить масштабирование."""
        if event.modifiers() & Qt.ControlModifier:
            # Игнорируем событие при Ctrl - пусть обрабатывает родитель (TimelineWidget)
            event.ignore()
        else:
            # Обычная прокрутка без Ctrl
            super().wheelEvent(event)


class SegmentGraphicsItem(QGraphicsRectItem):
    """Графический элемент сегмента с hover эффектами и tooltip."""
    def __init__(self, marker, timeline_scene):
        super().__init__()
        self.marker = marker
        self.timeline_scene = timeline_scene
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)

        event_manager = get_custom_event_manager()
        event = event_manager.get_event(marker.event_name)
        self.event_color = QColor(event.color) if event else QColor("#888888")
        self.is_hovered = False

        # Устанавливаем tooltip с полным текстом
        self.setToolTip(self._get_full_text())

    def boundingRect(self):
        """Возвращает bounding rect с отступами для предотвращения слипания."""
        rect = self.rect()
        return rect.adjusted(-2, -2, 2, 2)

    def _get_display_text(self):
        """Возвращает текст для отображения (note или название события)."""
        if self.marker.note and self.marker.note.strip():
            return self.marker.note.strip()
        else:
            event_manager = get_custom_event_manager()
            event = event_manager.get_event(self.marker.event_name)
            return event.get_localized_name() if event else self.marker.event_name

    def _get_full_text(self):
        """Возвращает полный текст для tooltip (включая и заметку и название события)."""
        event_manager = get_custom_event_manager()
        event = event_manager.get_event(self.marker.event_name)
        event_name = event.get_localized_name() if event else self.marker.event_name

        if self.marker.note and self.marker.note.strip():
            return f"{self.marker.note.strip()}\n({event_name})"
        else:
            return event_name

    def paint(self, painter, option, widget):
        """Отрисовка сегмента в стиле Hudl Sportscode."""
        rect = self.rect()

        # Определяем цвет заливки
        fill_color = self.event_color
        if self.is_hovered:
            fill_color = fill_color.lighter(120)  # Светлее при наведении

        # Устанавливаем полупрозрачность
        fill_color.setAlpha(200)

        # Рисуем скругленный прямоугольник с заливкой
        painter.setPen(Qt.NoPen)  # Без обводки
        painter.setBrush(QBrush(fill_color))
        painter.drawRoundedRect(rect, 4, 4)

        # Рисуем белую рамку при выделении
        if self.isSelected():
            selection_pen = QPen(QColor(Qt.white), 2, Qt.SolidLine)
            painter.setPen(selection_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, 1), 3, 3)

        # Рисуем текст
        painter.setPen(QPen(Qt.white))
        font = QFont("Segoe UI", 9, QFont.Normal)
        painter.setFont(font)

        text = self._get_display_text()
        font_metrics = QFontMetrics(font)

        # Если текст не помещается, обрезаем его
        available_width = rect.width() - 8
        if font_metrics.horizontalAdvance(text) > available_width:
            text = font_metrics.elidedText(text, Qt.ElideRight, available_width)

        # Выравниваем текст по левому краю с отступом, но не выходим за границы
        text_x = rect.left() + 4
        text_y = rect.center().y() + font_metrics.ascent() / 2

        painter.drawText(int(text_x), int(text_y), text)

    def hoverEnterEvent(self, event):
        self.is_hovered = True
        self.update()  # Перерисовываем
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hovered = False
        self.update()  # Перерисовываем
        super().hoverLeaveEvent(event)

    def mouseDoubleClickEvent(self, event):
        # MVC: emit signal instead of direct call
        # if self.timeline_scene.main_window:
        #     try:
        #         idx = self.timeline_scene.controller.markers.index(self.marker)
        #         self.timeline_scene.main_window.open_segment_editor(idx)
        #     except ValueError:
        #         pass
        pass  # Will be handled by controller


class TrackHeaderItem(QGraphicsObject):
    """Профессиональный заголовок трека с плоским дизайном."""

    HEADER_WIDTH = 140  # Фиксированная ширина заголовка

    def __init__(self, event, track_height):
        super().__init__()
        self.event_data = event  # Переименовано, чтобы не конфликтовать с методом event()
        self.track_height = track_height
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)  # Текст не искажается при зуме

        # Устанавливаем tooltip с полным названием события
        self.setToolTip(self.event_data.get_localized_name())

    def boundingRect(self):
        """Возвращает bounding rect заголовка."""
        return QRectF(0, 0, self.HEADER_WIDTH, self.track_height)

    def paint(self, painter, option, widget):
        """Отрисовка заголовка с плоским дизайном."""
        rect = self.boundingRect()

        # Темно-серый фон
        painter.fillRect(rect, QColor("#2a2a2a"))

        # Белый текст слева с отступом
        painter.setPen(QPen(Qt.white))
        font = QFont("Segoe UI", 10, QFont.Bold)
        painter.setFont(font)

        text = self.event_data.get_localized_name()
        font_metrics = QFontMetrics(font)

        # Если текст не помещается, обрезаем его
        available_width = self.HEADER_WIDTH - 20  # -20 для отступов (10px слева + 10px справа)
        if font_metrics.horizontalAdvance(text) > available_width:
            text = font_metrics.elidedText(text, Qt.ElideRight, available_width)

        # Центрируем текст вертикально
        text_x = 10
        text_y = rect.center().y() + font_metrics.ascent() / 2

        painter.drawText(int(text_x), int(text_y), text)


class TimelineGraphicsScene(QGraphicsScene):
    """Основная сцена таймлайна с профессиональной графикой."""

    # MVC Signals
    segment_double_clicked = Signal(Marker)  # When segment is double-clicked

    def __init__(self, controller=None):
        super().__init__()
        self.controller = controller
        self.main_window = None
        self.pixels_per_frame = 0.8
        self.track_height = 45
        self.header_height = 40

        # Playhead создаём один раз и больше НИКОГДА не удаляем!
        self.playhead = QGraphicsLineItem()
        self.playhead.setPen(QPen(QColor("#FFFF00"), 4, Qt.SolidLine, Qt.RoundCap))
        self.playhead.setZValue(1000)
        self.addItem(self.playhead)  # добавляем навсегда

        # Линия конца видео с подписью
        self.video_end_line = QGraphicsLineItem()
        self.video_end_line.setPen(QPen(QColor("#FF0000"), 3, Qt.SolidLine, Qt.RoundCap))
        self.video_end_line.setZValue(900)
        self.addItem(self.video_end_line)

        self.video_end_label = QGraphicsTextItem("Конец видео")
        self.video_end_label.setDefaultTextColor(QColor("#FF0000"))
        font = QFont("Segoe UI", 10, QFont.Bold)
        self.video_end_label.setFont(font)
        self.video_end_label.setZValue(900)
        self.addItem(self.video_end_label)

        self.rebuild()  # первый рендер

    def drawBackground(self, painter, rect):
        """Отрисовка фона с зеброй и сеткой времени."""
        super().drawBackground(painter, rect)

        # Получить список событий для определения количества треков
        events = get_custom_event_manager().get_all_events()
        if not events:
            return

        # Цвета зебры
        even_color = QColor("#1e1e1e")
        odd_color = QColor("#232323")

        # Рисуем полосы зебры только для видимой области
        for i in range(len(events)):
            y = i * self.track_height + 30  # +30 для линейки времени
            track_rect = QRectF(rect.left(), y, rect.width(), self.track_height)

            # Проверяем, пересекается ли полоса с видимой областью
            if track_rect.intersects(rect):
                color = even_color if i % 2 == 0 else odd_color
                painter.fillRect(track_rect, color)

        # Рисуем вертикальные линии сетки каждые 5 секунд
        fps = self.controller.get_fps() if self.controller else 30.0
        if fps > 0:
            grid_pen = QPen(QColor("#333333"), 1, Qt.SolidLine)
            painter.setPen(grid_pen)

            # Рассчитываем диапазон кадров для видимой области
            start_frame = max(0, int((rect.left() - 150) / self.pixels_per_frame))
            end_frame = int((rect.right() - 150) / self.pixels_per_frame) + 1

            # Находим первую отметку в 5 секунд до start_frame
            first_grid_seconds = (start_frame // int(5 * fps)) * 5
            current_seconds = first_grid_seconds

            while True:
                frame_index = int(current_seconds * fps)
                if frame_index > end_frame:
                    break

                x = frame_index * self.pixels_per_frame + 150
                if x >= rect.left() and x <= rect.right():
                    painter.drawLine(x, rect.top(), x, rect.bottom())

                current_seconds += 5

    def drawForeground(self, painter, rect):
        """Отрисовка линейки времени вверху."""
        super().drawForeground(painter, rect)

        # Линейка высотой 30px вверху (на Y=0)
        ruler_rect = QRectF(rect.left(), 0, rect.width(), 30)

        # Фон линейки
        painter.fillRect(ruler_rect, QColor("#1a1a1a"))

        # Рисуем засечки и время каждые 5 секунд
        fps = self.controller.get_fps() if self.controller else 30.0
        if fps > 0:
            # Рассчитываем диапазон для видимой области
            start_frame = max(0, int((rect.left() - 150) / self.pixels_per_frame))
            end_frame = int((rect.right() - 150) / self.pixels_per_frame) + 1

            # Находим первую отметку в 5 секунд
            first_grid_seconds = (start_frame // int(5 * fps)) * 5
            current_seconds = first_grid_seconds

            while True:
                frame_index = int(current_seconds * fps)
                if frame_index > end_frame:
                    break

                x = frame_index * self.pixels_per_frame + 150
                if x >= rect.left() and x <= rect.right():
                    # Засечка
                    painter.setPen(QPen(QColor("#666666"), 1, Qt.SolidLine))
                    painter.drawLine(x, 25, x, 30)  # засечка 5px высотой

                    # Время в формате MM:SS
                    minutes = current_seconds // 60
                    seconds = current_seconds % 60
                    time_text = f"{minutes:02d}:{seconds:02d}"

                    # Рисуем текст
                    painter.setPen(QPen(Qt.white))
                    font = QFont("Segoe UI", 8, QFont.Normal)
                    painter.setFont(font)

                    # Позиция текста чуть выше засечки
                    text_x = x - 15  # центрируем относительно засечки
                    painter.drawText(int(text_x), 20, time_text)

                current_seconds += 5

    def rebuild(self):
        """Перестроение всей сцены."""
        total_frames = max(self.controller.get_total_frames() if self.controller else 1000, 1)
        events = get_custom_event_manager().get_all_events()

        # Очищаем всё КРОМЕ playhead, video_end_line и video_end_label
        for item in self.items():
            if item not in (self.playhead, self.video_end_line, self.video_end_label):
                self.removeItem(item)

        scene_width = total_frames * self.pixels_per_frame + 300
        scene_height = len(events) * self.track_height + self.header_height + 50 + 30  # +30 для линейки
        self.setSceneRect(0, 0, scene_width, scene_height)

        # Позиционируем линию конца видео и подпись
        end_x = (total_frames - 1) * self.pixels_per_frame + 150
        self.video_end_line.setLine(end_x, 0, end_x, scene_height)
        self.video_end_label.setPos(end_x - 35, -5)  # Подпись чуть выше линии

        track_bg = QColor("#0d1b2a")

        for i, event in enumerate(events):
            y = i * self.track_height + 30  # +30 для линейки времени

            # Заголовок события с плоским дизайном
            header = TrackHeaderItem(event, self.track_height)
            header.setPos(0, y)
            self.addItem(header)

            # Сегменты
            if self.controller:
                for marker in self.controller.markers:
                    if marker.event_name != event.name:
                        continue
                    x = marker.start_frame * self.pixels_per_frame
                    w = (marker.end_frame - marker.start_frame + 1) * self.pixels_per_frame
                    if w < 10: w = 10

                    segment = SegmentGraphicsItem(marker, self)
                    segment.setRect(x + 150, y + 8, w, self.track_height - 16)
                    self.addItem(segment)

        self.update_playhead(self.controller.get_current_frame_idx() if self.controller else 0)

    def update_playhead(self, frame_idx: int):
        """Обновление позиции плейхеда."""
        if frame_idx < 0:
            return
        x = frame_idx * self.pixels_per_frame + 150
        self.playhead.setLine(x, 0.0, x, self.sceneRect().height())

        # Также обновляем позицию линии конца видео
        total_frames = max(self.controller.get_total_frames() if self.controller else 1000, 1)
        end_x = (total_frames - 1) * self.pixels_per_frame + 150
        self.video_end_line.setLine(end_x, 0.0, end_x, self.sceneRect().height())
        self.video_end_label.setPos(end_x - 35, -5)


class TimelineWidget(QWidget):
    """Главный виджет таймлайна - точная копия из старого проекта."""

    # MVC Signals
    seek_requested = Signal(int)  # Frame to seek to
    segment_edit_requested = Signal(Marker)  # Segment double-clicked

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
        self.scene.main_window = self  # для двойного клика
        self.scene.segment_double_clicked.connect(self.segment_edit_requested)
        self.view.setScene(self.scene)

        scroll = TimelineScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.view)
        layout.addWidget(scroll)

        # === Подписки на обновления ===
        if controller:
            controller.markers_changed.connect(self.scene.rebuild)
            controller.playback_time_changed.connect(lambda f: self.scene.update_playhead(f))
            controller.timeline_update.connect(lambda: self.scene.update_playhead(controller.get_current_frame_idx()))
        get_custom_event_manager().events_changed.connect(self.scene.rebuild)

        # Масштабирование
        self.scale_factor = 1.0

    def get_pixels_per_frame(self) -> float:
        """Get current pixels per frame ratio.

        Returns:
            Current zoom level
        """
        return self.scene.get_pixels_per_frame()

    def set_total_frames(self, total_frames: int) -> None:
        """Обновляет ширину сцены в зависимости от количества кадров видео"""
        if total_frames < 1:
            total_frames = 1000  # fallback

        scene = self.scene
        if not scene:
            return

        # Масштаб хранится в сцене
        ppf = scene.pixels_per_frame
        scene_width = max(1000, total_frames * ppf + 300)  # + запас справа

        current_rect = scene.sceneRect()
        scene.setSceneRect(0, 0, scene_width, current_rect.height())

        # Перестраиваем, чтобы линии конца видео и т.п. обновились
        scene.rebuild()

    def set_current_frame(self, frame: int, fps: float) -> None:
        """Set the current frame and update the playhead.

        Args:
            frame: Current frame number
            fps: Frames per second
        """
        self.scene.update_playhead(frame)

    def init_tracks(self, track_names, total_frames, fps):
        """Initialize tracks for the timeline."""
        if self.scene:
            self.scene.rebuild()

    def set_markers(self, markers):
        """Set markers on the timeline."""
        # Markers are handled in rebuild, so just rebuild
        self.scene.rebuild()

    def set_fps(self, fps: float) -> None:
        """Устанавливает FPS и перестраивает таймлайн (линейку времени и т.д.)"""
        if self.scene and self.scene.controller:
            # В новой реализации FPS используется внутри сцены
            self.scene.rebuild()  # перестроим сцену с учётом нового fps
        # Если нужно сохранить fps где-то ещё — можно добавить атрибут
        # self.fps = fps

    def wheelEvent(self, event):
        """Масштабирование Ctrl+колесо."""
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.25 if event.angleDelta().y() > 0 else 0.8
            self.scale_factor *= factor
            self.scene.pixels_per_frame *= factor
            self.scene.rebuild()

            # Автоскролл к плейхеду
            if self.controller:
                current_x = self.controller.get_current_frame_idx() * self.scene.pixels_per_frame + 150
                self.view.horizontalScrollBar().setValue(int(current_x - self.view.width() // 2))

            # Заблокировать прокрутку QScrollArea при масштабировании
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Клик по таймлайну для перехода к времени."""
        if event.button() == Qt.LeftButton:
            pos = self.view.mapToScene(self.view.mapFrom(self, event.pos()))
            frame = int((pos.x() - 150) / self.scene.pixels_per_frame)
            if self.controller:
                frame = max(0, min(frame, self.controller.get_total_frames() - 1))
                self.seek_requested.emit(frame)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        """Правый клик - контекстное меню."""
        menu = QMenu(self)

        # Действия контекстного меню
        if self.controller:
            save_action = QAction("Сохранить проект", self)
            save_action.triggered.connect(self.controller.save_project)
            menu.addAction(save_action)

            open_action = QAction("Открыть проект", self)
            open_action.triggered.connect(self.controller.load_project)
            menu.addAction(open_action)

            new_action = QAction("Новый проект", self)
            new_action.triggered.connect(self.controller.new_project)
            menu.addAction(new_action)

        # Показываем меню в позиции курсора
        menu.exec(event.globalPos())

    # MVC Methods
    def set_controller(self, controller):
        """Set controller for MVC pattern."""
        self.controller = controller
        self.scene.controller = controller

        # Reconnect signals
        if controller:
            controller.markers_changed.connect(self.scene.rebuild)
            controller.playback_time_changed.connect(lambda f: self.scene.update_playhead(f))
            controller.timeline_update.connect(lambda: self.scene.update_playhead(controller.get_current_frame_idx()))

        self.scene.rebuild()

        # Set initial scene size
        self.scene.setSceneRect(0, 0, 1000, 200)

    def draw_ruler(self) -> None:
        """Draw the time ruler at the top of the timeline."""
        # Clear existing ruler items
        for item in self.ruler_items + self.ruler_text_items:
            self.scene.removeItem(item)
        self.ruler_items.clear()
        self.ruler_text_items.clear()

        # Ruler background
        ruler_bg = self.scene.addRect(0, 0, self.scene.width(), self.ruler_height,
                                    QPen(Qt.PenStyle.NoPen),
                                    QBrush(QColor(AppColors.BACKGROUND)))

        # Draw time marks every 5 seconds
        if self.fps > 0:
            current_time = 0
            while True:
                frame = int(current_time * self.fps)
                x_pos = frame * self.pixels_per_frame

                # Stop if we're beyond the visible area
                if x_pos > self.scene.width():
                    break

                # Major tick (every 5 seconds)
                if current_time % 5 == 0:
                    # Draw tick mark
                    tick = self.scene.addLine(x_pos, self.ruler_height - 10,
                                           x_pos, self.ruler_height,
                                           QPen(QColor(AppColors.TEXT), 2))
                    self.ruler_items.append(tick)

                    # Draw time text
                    time_text = f"{int(current_time // 60):02d}:{int(current_time % 60):02d}"
                    text_item = self.scene.addText(time_text)
                    text_item.setDefaultTextColor(QColor(AppColors.TEXT))
                    text_item.setFont(QFont("Segoe UI", 8))
                    text_item.setPos(x_pos - 15, 5)
                    self.ruler_text_items.append(text_item)

                # Minor tick (every second)
                elif current_time % 1 == 0:
                    tick = self.scene.addLine(x_pos, self.ruler_height - 5,
                                           x_pos, self.ruler_height,
                                           QPen(QColor(AppColors.BORDER), 1))
                    self.ruler_items.append(tick)

                current_time += 1

    def draw_playhead(self, frame: int) -> None:
        """Draw or update the playhead at the specified frame."""
        x_pos = frame * self.pixels_per_frame

        # Remove existing playhead
        if self.playhead:
            self.scene.removeItem(self.playhead)

        # Create new playhead
        self.playhead = self.scene.addLine(x_pos, 0, x_pos, self.scene.height(),
                                        QPen(QColor("#FFFF00"), 3))  # Yellow playhead

        # Bring playhead to front
        if self.playhead:
            self.playhead.setZValue(1000)

    def set_segments(self, segments: List[Marker]) -> None:
        """Set the segments to display on the timeline.

        Args:
            segments: List of Marker objects representing video segments
        """
        # Clear existing segments
        for item in self.segment_items:
            self.scene.removeItem(item)
        self.segment_items.clear()

        # Group segments by event type for tracks
        event_tracks = {}
        track_index = 0

        # Import event manager to get colors
        from services.events.custom_event_manager import get_custom_event_manager
        event_manager = get_custom_event_manager()

        # Process each segment
        for segment in segments:
            event_name = segment.event_name

            # Get or create track for this event type
            if event_name not in event_tracks:
                event_tracks[event_name] = track_index
                track_index += 1

            track_y = self.ruler_height + (event_tracks[event_name] * self.track_height)

            # Calculate segment position and size
            start_x = segment.start_frame * self.pixels_per_frame
            width = (segment.end_frame - segment.start_frame + 1) * self.pixels_per_frame
            if width < 5:  # Minimum width
                width = 5

            # Create rectangle for segment
            rect_item = QGraphicsRectItem(start_x, track_y + 5, width, self.track_height - 10)

            # Set color based on event type
            segment_color = QColor(AppColors.ACCENT)  # Default color
            if event_manager:
                event = event_manager.get_event(event_name)
                if event:
                    segment_color = QColor(event.color)

            # Semi-transparent fill
            segment_color.setAlpha(180)
            rect_item.setBrush(QBrush(segment_color))
            rect_item.setPen(QPen(QColor(AppColors.TEXT), 1))

            # Add tooltip
            rect_item.setToolTip(f"{event_name}: {segment.start_frame}-{segment.end_frame}")

            # Add to scene
            self.scene.addItem(rect_item)
            self.segment_items.append(rect_item)

        # Update scene height based on number of tracks
        scene_height = self.ruler_height + (len(event_tracks) * self.track_height) + 20
        current_rect = self.scene.sceneRect()
        self.scene.setSceneRect(0, 0, max(current_rect.width(), 1000), scene_height)

        # Redraw ruler and playhead
        self.draw_ruler()
        if self.playhead:
            self.draw_playhead(int(self.playhead.line().x1() / self.pixels_per_frame))

    def update_segment(self, index: int, marker: Marker) -> None:
        """Update a specific segment by index without full redraw.

        Args:
            index: Index of the segment to update
            marker: The marker data to update with
        """
        if 0 <= index < len(self.segment_items):
            self._update_segment_item(self.segment_items[index], marker)
        else:
            # If index is out of range, add new segment
            self._add_segment_item(marker)

    def remove_segment(self, index: int) -> None:
        """Remove a specific segment by index.

        Args:
            index: Index of the segment to remove
        """
        if 0 <= index < len(self.segment_items):
            item = self.segment_items.pop(index)
            self.scene.removeItem(item)

    def clear_segments(self) -> None:
        """Clear all segments from the timeline."""
        for item in self.segment_items:
            self.scene.removeItem(item)
        self.segment_items.clear()

    def update_segment_optimized(self, marker: Marker, index: int) -> None:
        """Optimized update of a specific segment without full redraw."""
        if 0 <= index < len(self.segment_items):
            # Update existing segment
            self._update_segment_item(self.segment_items[index], marker)
        else:
            # Add new segment
            self._add_segment_item(marker)

    def _update_segment_item(self, rect_item: QGraphicsRectItem, marker: Marker) -> None:
        """Update an existing segment item with new marker data."""
        # Group segments by event type for tracks
        event_tracks = {}
        track_index = 0
        
        # Find track for this event type
        for seg in self._get_current_segments():
            if seg.event_name not in event_tracks:
                event_tracks[seg.event_name] = track_index
                track_index += 1

        # Get track for current marker
        if marker.event_name not in event_tracks:
            event_tracks[marker.event_name] = track_index

        track_y = self.ruler_height + (event_tracks[marker.event_name] * self.track_height)

        # Calculate new position and size
        start_x = marker.start_frame * self.pixels_per_frame
        width = (marker.end_frame - marker.start_frame + 1) * self.pixels_per_frame
        if width < 5:  # Minimum width
            width = 5

        # Update rectangle
        rect_item.setRect(start_x, track_y + 5, width, self.track_height - 10)

        # Update color based on event type
        segment_color = QColor(AppColors.ACCENT)  # Default color
        from services.events.custom_event_manager import get_custom_event_manager
        event_manager = get_custom_event_manager()
        if event_manager:
            event = event_manager.get_event(marker.event_name)
            if event:
                segment_color = QColor(event.color)

        # Semi-transparent fill
        segment_color.setAlpha(180)
        rect_item.setBrush(QBrush(segment_color))
        rect_item.setPen(QPen(QColor(AppColors.TEXT), 1))

        # Update tooltip
        rect_item.setToolTip(f"{marker.event_name}: {marker.start_frame}-{marker.end_frame}")

    def _add_segment_item(self, marker: Marker) -> None:
        """Add a new segment item to the timeline."""
        # Group segments by event type for tracks
        event_tracks = {}
        track_index = 0
        
        # Include new marker in track calculation
        all_markers = self._get_current_segments() + [marker]
        
        for seg in all_markers:
            if seg.event_name not in event_tracks:
                event_tracks[seg.event_name] = track_index
                track_index += 1

        track_y = self.ruler_height + (event_tracks[marker.event_name] * self.track_height)

        # Calculate position and size
        start_x = marker.start_frame * self.pixels_per_frame
        width = (marker.end_frame - marker.start_frame + 1) * self.pixels_per_frame
        if width < 5:  # Minimum width
            width = 5

        # Create rectangle for segment
        rect_item = QGraphicsRectItem(start_x, track_y + 5, width, self.track_height - 10)

        # Set color based on event type
        segment_color = QColor(AppColors.ACCENT)  # Default color
        from services.events.custom_event_manager import get_custom_event_manager
        event_manager = get_custom_event_manager()
        if event_manager:
            event = event_manager.get_event(marker.event_name)
            if event:
                segment_color = QColor(event.color)

        # Semi-transparent fill
        segment_color.setAlpha(180)
        rect_item.setBrush(QBrush(segment_color))
        rect_item.setPen(QPen(QColor(AppColors.TEXT), 1))

        # Add tooltip
        rect_item.setToolTip(f"{marker.event_name}: {marker.start_frame}-{marker.end_frame}")

        # Add to scene and list
        self.scene.addItem(rect_item)
        self.segment_items.append(rect_item)

        # Update scene height if needed
        self._update_scene_height(event_tracks)

    def _get_current_segments(self) -> List[Marker]:
        """Get current segments from the timeline."""
        # This is a simplified version - in practice, you might want to store
        # the original markers list or use a different approach
        return []

    def _update_scene_height(self, event_tracks: dict) -> None:
        """Update scene height based on number of tracks."""
        scene_height = self.ruler_height + (len(event_tracks) * self.track_height) + 20
        current_rect = self.scene.sceneRect()
        self.scene.setSceneRect(0, 0, current_rect.width(), scene_height)

    def get_pixels_per_frame(self) -> float:
        """Get current pixels per frame ratio.

        Returns:
            Current zoom level
        """
        return self.pixels_per_frame

    def set_zoom(self, pixels_per_frame: float) -> None:
        """Set the zoom level.

        Args:
            pixels_per_frame: New pixels per frame ratio
        """
        self.pixels_per_frame = max(0.1, min(5.0, pixels_per_frame))
        self.set_segments([])  # Trigger redraw
        self.draw_ruler()

    def clear_timeline(self) -> None:
        """Clear all segments from the timeline."""
        for item in self.segment_items:
            self.scene.removeItem(item)
        self.segment_items.clear()

        # Reset scene size
        self.scene.setSceneRect(0, 0, 1000, self.ruler_height + 20)

    def rebuild(self, animate_new: bool = True) -> None:
        """Rebuild the entire timeline scene.
        
        This method clears the existing scene content and redraws all
        timeline elements including ruler, tracks, and segments.
        
        Args:
            animate_new: Currently unused - kept for compatibility
        """
        # Clear all existing items from scene
        self.scene.clear()
        
        # Reinitialize graphics items lists
        self.playhead = None
        self.segment_items.clear()
        self.ruler_items.clear()
        self.ruler_text_items.clear()
        # Redraw the timeline
        self._setup_timeline()

    def _setup_timeline(self) -> None:
        """Setup the timeline graphics."""
        # Reinitialize playhead and end line
        self.playhead = QGraphicsLineItem()
        self.playhead.setPen(QPen(QColor("#FFFF00"), 4, Qt.SolidLine, Qt.RoundCap))
        self.playhead.setZValue(1000)
        self.addItem(self.playhead)

        # Video end line
        self.video_end_line = QGraphicsLineItem()
        self.video_end_line.setPen(QPen(QColor("#FF0000"), 2))
        self.addItem(self.video_end_line)

        self.video_end_label = QGraphicsTextItem("END")
        self.video_end_label.setDefaultTextColor(QColor("#FF0000"))
        self.addItem(self.video_end_label)

        # Initialize lists
        self.segment_items = []
        self.ruler_items = []
        self.ruler_text_items = []

        # Setup tracks and segments
        self._setup_tracks_and_segments()

    def _setup_tracks_and_segments(self) -> None:
        """Setup tracks and segments."""
        # This is a placeholder - implement based on old code
        pass

