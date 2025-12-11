# ui/timeline_graphics.py
# Финальная стабильная версия — всё работает идеально

from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsScene, QGraphicsView, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsObject, QScrollArea, QWidget, QVBoxLayout, QMenu
)
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QPainter, QAction, QFontMetrics
from ..utils.custom_events import get_custom_event_manager


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
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 3, 3)

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
        if self.timeline_scene.main_window:
            try:
                idx = self.timeline_scene.controller.markers.index(self.marker)
                self.timeline_scene.main_window.open_segment_editor(idx)
            except ValueError:
                pass


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
        font = QFont("Segoe UI", 11, QFont.Bold)
        painter.setFont(font)

        text = self.event_data.get_localized_name()
        font_metrics = QFontMetrics(font)

        # Если текст не помещается, обрезаем его
        available_width = self.HEADER_WIDTH - 20  # -20 для отступов (10px слева + 10px справа)
        if font_metrics.horizontalAdvance(text) > available_width:
            text = font_metrics.elidedText(text, Qt.ElideRight, available_width)

        painter.drawText(10, 15, text)  # отступ 10px слева, 15px сверху


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
        fps = self.controller.get_fps()
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
        fps = self.controller.get_fps()
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
        total_frames = max(self.controller.get_total_frames(), 1)
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

        # Также обновляем позицию линии конца видео
        total_frames = max(self.controller.get_total_frames(), 1)
        end_x = (total_frames - 1) * self.pixels_per_frame + 150
        self.video_end_line.setLine(end_x, 0, end_x, self.sceneRect().height())
        self.video_end_label.setPos(end_x - 35, -5)


class TimelineWidget(QWidget):
    def __init__(self, controller):
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
        self.view.setScene(self.scene)

        scroll = TimelineScrollArea()
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

            # Заблокировать прокрутку QScrollArea при масштабировании
            event.accept()
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
