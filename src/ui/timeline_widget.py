from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from pyqtgraph import PlotWidget, BarGraphItem, mkPen
from typing import List
from ..models.event import Event

class TimelineWidget(QWidget):
    event_clicked = pyqtSignal(str)
    event_edited = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.events: List[Event] = []
        self.current_position = 0.0
        self.duration = 0.0
        self.zoom_level = 1.0
        layout = QVBoxLayout()
        self.plot = PlotWidget()
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def set_duration(self, duration: float):
        self.duration = duration
        self.plot.setXRange(0, duration)

    def set_events(self, events: List[Event]):
        self.events = events
        self._update_plot()

    def set_current_position(self, position: float):
        self.current_position = position
        self.plot.addLine(x=position, pen=mkPen('y', width=2))

    def _update_plot(self):
        self.plot.clear()
        for event in self.events:
            bar = BarGraphItem(x=[event.actual_start, event.actual_end], height=1, width=(event.actual_end - event.actual_start), brush=event.color)
            self.plot.addItem(bar)

    def paintEvent(self, event):
        """Отрисовка таймлайна"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Фон
        painter.fillRect(self.rect(), QColor(40, 40, 40))
        
        # Сетка временных меток
        self._draw_timeline(painter)
        
        # События
        self._draw_events(painter)
        
        # Текущая позиция
        self._draw_current_position(painter)

    def _draw_timeline(self, painter: QPainter):
        """Отрисовка временной сетки"""
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        
        # Расчет интервала между метками
        time_per_pixel = self.duration / (self.width() / self.zoom)
        interval = self._calculate_interval(time_per_pixel)
        
        y_start = 20
        for i in range(0, int(self.duration) + 1, max(1, int(interval))):
            x = (i / self.duration) * (self.width() / self.zoom)
            if 0 <= x < self.width():
                painter.drawLine(int(x), y_start - 5, int(x), y_start)
                
                # Текст времени
                time_str = self._seconds_to_timecode(i)
                painter.setFont(QFont("Arial", 8))
                painter.drawText(int(x) - 20, y_start - 25, 40, 20, Qt.AlignmentFlag.AlignCenter, time_str)

    def _draw_events(self, painter: QPainter):
        """Отрисовка событий"""
        y_offset = 50
        row_height = config.TIMELINE_HEIGHT
        
        # Группировка событий по типам
        event_types = {}
        for event in self.events:
            if event.event_type not in event_types:
                event_types[event.event_type] = []
            event_types[event.event_type].append(event)
        
        row = 0
        for event_type, events_in_type in event_types.items():
            y = y_offset + row * row_height
            
            # Фон строки
            painter.fillRect(0, y, self.width(), row_height, QColor(50, 50, 50))
            painter.drawLine(0, y + row_height, self.width(), y + row_height)
            
            # Название типа события
            painter.setFont(QFont("Arial", 9))
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(5, y + 5, 150, 20, Qt.AlignmentFlag.AlignLeft, event_type)
            
            # События в строке
            for event in events_in_type:
                self._draw_event_bar(painter, event, y + 25)
            
            row += 1

    def _draw_event_bar(self, painter: QPainter, event, y: int):
        """Отрисовка отдельного события"""
        # Расчет позиции на экране
        start_x = (event.start_time / self.duration) * (self.width() / self.zoom)
        end_x = (event.end_time / self.duration) * (self.width() / self.zoom)
        
        # Проверка видимости
        if end_x < 0 or start_x > self.width():
            return
        
        bar_height = 20
        x = int(max(0, start_x))
        width = int(min(self.width(), end_x) - x)
        
        # Рисование прямоугольника события
        color = QColor(event.color)
        painter.fillRect(x, y, width, bar_height, color)
        
        # Выделение если выбрано
        if self.selected_event and self.selected_event.id == event.id:
            painter.setPen(QPen(QColor(255, 255, 255), 3))
            painter.drawRect(x, y, width, bar_height)
        else:
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.drawRect(x, y, width, bar_height)
        
        # Текст события
        if width > 30:
            painter.setFont(QFont("Arial", 8))
            painter.setPen(QColor(0, 0, 0))
            painter.drawText(x + 2, y + 2, width - 4, bar_height - 4, 
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, 
                           event.name)

    def _draw_current_position(self, painter: QPainter):
        """Отрисовка текущей позиции воспроизведения"""
        if self.duration > 0:
            x = (self.current_position / self.duration) * (self.width() / self.zoom)
            painter.setPen(QPen(QColor(255, 0, 0), 2))
            painter.drawLine(int(x), 0, int(x), self.height())

    def wheelEvent(self, event):
        """Масштабирование по Ctrl+колесо мыши"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Масштабирование
            delta = event.angleDelta().y()
            zoom_factor = 1.1 if delta > 0 else 0.9
            new_zoom = self.zoom * zoom_factor
            
            if config.MIN_ZOOM <= new_zoom <= config.MAX_ZOOM:
                self.zoom = new_zoom
                self.update()
            event.accept()

    def mousePressEvent(self, event):
        """Нажатие мыши"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Проверка клика по событию
            for event_obj in self.events:
                if self._is_point_on_event(event.pos(), event_obj):
                    self.selected_event = event_obj
                    self.event_clicked.emit(event_obj.id)
                    self.update()
                    break

    def mouseMoveEvent(self, event):
        """Движение мыши"""
        if self.selected_event and event.buttons() & Qt.MouseButton.LeftButton:
            # Перетаскивание границ события
            time = self._pixel_to_time(event.pos().x())
            if abs(event.pos().x() - self._time_to_pixel(self.selected_event.start_time)) < 10:
                self.dragging_edge = 'start'
                self.selected_event.start_time = max(0, time)
            elif abs(event.pos().x() - self._time_to_pixel(self.selected_event.end_time)) < 10:
                self.dragging_edge = 'end'
                self.selected_event.end_time = min(self.duration, time)
            
            self.update()

    def mouseDoubleClickEvent(self, event):
        """Двойной клик для редактирования"""
        for event_obj in self.events:
            if self._is_point_on_event(event.pos(), event_obj):
                self.selected_event = event_obj
                # Сигнал для открытия диалога редактирования
                self.event_edited.emit(event_obj.id, {'action': 'edit'})
                break

    def _is_point_on_event(self, point: QPoint, event_obj) -> bool:
        """Проверить, находится ли точка на событии"""
        start_x = self._time_to_pixel(event_obj.start_time)
        end_x = self._time_to_pixel(event_obj.end_time)
        
        return start_x <= point.x() <= end_x and 50 <= point.y() <= self.height()

    def _time_to_pixel(self, time: float) -> int:
        """Преобразовать время в позицию пикселя"""
        return int((time / self.duration) * (self.width() / self.zoom))

    def _pixel_to_time(self, pixel: int) -> float:
        """Преобразовать позицию пикселя в время"""
        return (pixel / (self.width() / self.zoom)) * self.duration

    @staticmethod
    def _calculate_interval(time_per_pixel: float) -> int:
        """Расчет интервала для временной сетки"""
        if time_per_pixel < 1:
            return 1
        elif time_per_pixel < 5:
            return 5
        elif time_per_pixel < 10:
            return 10
        else:
            return 60

    @staticmethod
    def _seconds_to_timecode(seconds: float) -> str:
        """Преобразовать секунды в HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
