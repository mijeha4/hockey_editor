from PySide6.QtCore import Qt, QSize, QTimer, QRect
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import QWidget
from typing import Optional


class TimelineWidget(QWidget):
    """Профессиональный многострочный таймлайн (как в SportCode)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.controller = None
        
        # Параметры отрисовки
        self.track_height = 50
        self.header_height = 30
        self.pixels_per_second = 100
        self.zoom = 1.0
        self.scroll_x = 0
        
        # Мигание при записи
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self._on_blink_tick)
        self.blink_visible = True
        self.blink_interval = 500  # мс
        
        # Цвета дорожек
        self.colors = {
            'ATTACK': QColor(139, 0, 0),      # Тёмно-красный
            'DEFENSE': QColor(0, 0, 128),     # Тёмно-синий
            'SHIFT': QColor(0, 100, 0),       # Тёмно-зелёный
            'PLAYHEAD': QColor(255, 255, 0),  # Жёлтый
            'REC': QColor(255, 200, 0),       # Жёлто-оранжевый
            'SEGMENT': QColor(255, 255, 255), # Белый
        }
        
        self.setMinimumHeight(self.header_height + 3 * self.track_height)
        self.setStyleSheet("background-color: #1a1a1a; border: none;")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_controller(self, controller):
        """Установить контроллер видео."""
        self.controller = controller
        if controller:
            controller.timeline_update.connect(self.update)
            controller.playback_time_changed.connect(lambda _: self.update())
            controller.markers_changed.connect(self.update)
            controller.recording_status_changed.connect(self._on_recording_status_changed)

    def _on_recording_status_changed(self, event_type: str, status: str):
        """Обновление при изменении статуса записи."""
        if status == "Recording":
            self.blink_timer.start(self.blink_interval)
        elif status in ("Complete", "Fixed", "Cancelled"):
            self.blink_timer.stop()
            self.blink_visible = True
        self.update()

    def _on_blink_tick(self):
        """Мигание REC при записи."""
        self.blink_visible = not self.blink_visible
        self.update()

    def paintEvent(self, event):
        """Отрисовка таймлайна."""
        if not self.controller or not self.controller.processor.cap:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Фон
        painter.fillRect(self.rect(), QColor(26, 26, 26))
        
        # Рисование временной шкалы
        self._draw_timeline_header(painter)
        
        # Рисование дорожек
        self._draw_tracks(painter)

    def _draw_timeline_header(self, painter: QPainter):
        """Отрисовка временной шкалы."""
        header_rect = QRect(0, 0, self.width(), self.header_height)
        painter.fillRect(header_rect, QColor(35, 35, 35))
        painter.drawLine(0, self.header_height - 1, self.width(), self.header_height - 1)
        
        # Расчёт времени
        total_frames = self.controller.get_total_frames()
        fps = self.controller.get_fps()
        total_time = total_frames / fps if fps > 0 else 0
        
        # Метки времени
        painter.setPen(QColor(150, 150, 150))
        painter.setFont(QFont("Arial", 8))
        
        pixels_per_sec_with_zoom = self.pixels_per_second * self.zoom
        time_step = 5  # Метки каждые 5 секунд
        
        for sec in range(0, int(total_time) + time_step, time_step):
            x = sec * pixels_per_sec_with_zoom - self.scroll_x
            if 0 <= x <= self.width():
                painter.drawLine(int(x), self.header_height - 5, int(x), self.header_height)
                time_str = self._format_time(sec)
                painter.drawText(int(x) - 15, 10, 30, 15, Qt.AlignmentFlag.AlignCenter, time_str)

    def _draw_tracks(self, painter: QPainter):
        """Отрисовка дорожек с отрезками."""
        tracks = ['ATTACK', 'DEFENSE', 'SHIFT']
        
        for idx, track_name in enumerate(tracks):
            track_y = self.header_height + idx * self.track_height
            track_rect = QRect(0, track_y, self.width(), self.track_height)
            
            # Фон дорожки
            color = self.colors[track_name]
            bg_color = QColor(color)
            bg_color.setAlpha(30)
            painter.fillRect(track_rect, bg_color)
            painter.drawRect(track_rect)
            
            # Метка дорожки (слева)
            label_rect = QRect(5, track_y, 80, self.track_height)
            painter.setPen(color)
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignVCenter, track_name)
        
        # Отрисовка отрезков
        self._draw_segments(painter, tracks)
        
        # Отрисовка playhead
        self._draw_playhead(painter)
        
        # Отрисовка растущего отрезка при записи
        if self.controller.is_recording:
            self._draw_recording_indicator(painter, tracks)

    def _draw_segments(self, painter: QPainter, tracks: list):
        """Отрисовка завершённых отрезков."""
        fps = self.controller.get_fps()
        if fps == 0:
            return
        
        pixels_per_sec = self.pixels_per_second * self.zoom
        
        for marker in self.controller.markers:
            track_idx = tracks.index(marker.type.name)
            track_y = self.header_height + track_idx * self.track_height
            
            # Позиции в пикселях
            start_x = (marker.start_frame / fps) * pixels_per_sec - self.scroll_x
            end_x = (marker.end_frame / fps) * pixels_per_sec - self.scroll_x
            width = max(2, end_x - start_x)
            
            # Рисование полоски
            segment_rect = QRect(int(start_x), track_y + 5, int(width), self.track_height - 10)
            color = self.colors[marker.type.name]
            painter.fillRect(segment_rect, self.colors['SEGMENT'])
            painter.setPen(color)
            painter.drawRect(segment_rect)

    def _draw_playhead(self, painter: QPainter):
        """Отрисовка playhead (жёлтая линия)."""
        fps = self.controller.get_fps()
        current_frame = self.controller.get_current_frame_idx()
        
        if fps == 0:
            return
        
        pixels_per_sec = self.pixels_per_second * self.zoom
        playhead_x = (current_frame / fps) * pixels_per_sec - self.scroll_x
        
        painter.setPen(QPen(self.colors['PLAYHEAD'], 2))
        painter.drawLine(int(playhead_x), self.header_height, int(playhead_x), self.height())

    def _draw_recording_indicator(self, painter: QPainter, tracks: list):
        """Отрисовка растущего отрезка при записи."""
        if not self.controller.recording_event_type or self.controller.recording_start_frame is None:
            return
        
        fps = self.controller.get_fps()
        if fps == 0:
            return
        
        pixels_per_sec = self.pixels_per_second * self.zoom
        track_idx = tracks.index(self.controller.recording_event_type.name)
        track_y = self.header_height + track_idx * self.track_height
        
        # Начало и конец текущей записи
        current_frame = self.controller.get_current_frame_idx()
        start_x = (self.controller.recording_start_frame / fps) * pixels_per_sec - self.scroll_x
        end_x = (current_frame / fps) * pixels_per_sec - self.scroll_x
        width = max(2, end_x - start_x)
        
        # Рисование растущей полоски
        rec_rect = QRect(int(start_x), track_y + 5, int(width), self.track_height - 10)
        painter.fillRect(rec_rect, self.colors['REC'])
        
        # Мигающий текст REC
        if self.blink_visible:
            painter.setPen(QColor(255, 0, 0))
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.drawText(rec_rect, Qt.AlignmentFlag.AlignCenter, "🔴 REC")

    def _format_time(self, seconds: int) -> str:
        """Конвертировать секунды в MM:SS."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    def mousePressEvent(self, event):
        """Клик на таймлайн = seek."""
        if not self.controller or not self.controller.processor.cap:
            return
        
        # Определить клик по дорожке
        if event.y() < self.header_height:
            return
        
        # Конвертировать x в фрейм
        fps = self.controller.get_fps()
        if fps == 0:
            return
        
        pixels_per_sec = self.pixels_per_second * self.zoom
        seconds = (event.x() + self.scroll_x) / pixels_per_sec
        frame_idx = int(seconds * fps)
        
        self.controller.seek_frame(frame_idx)

    def wheelEvent(self, event):
        """Масштабирование колесом мыши (Ctrl+Wheel)."""
        if event.modifiers() != Qt.KeyboardModifier.ControlModifier:
            return

        # Zoom
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom = min(self.zoom * 1.2, 10.0)
        else:
            self.zoom = max(self.zoom / 1.2, 1.0)

        # Заблокировать прокрутку при масштабировании
        event.accept()
        self.update()

    def sizeHint(self) -> QSize:
        """Размер по умолчанию."""
        return QSize(800, self.header_height + 3 * self.track_height)
