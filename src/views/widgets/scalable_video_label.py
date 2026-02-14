"""
ScalableVideoLabel - виджет для отображения видео с автоматическим масштабированием.

Этот виджет заменяет QLabel для отображения видео, обеспечивая:
- Автоматическое масштабирование с сохранением пропорций
- Центрирование изображения
- Эффективную перерисовку при изменении размеров
- Поддержку OpenCV кадров (BGR -> RGB конвертацию)
"""

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPixmap, QImage, QPaintEvent, QResizeEvent
from PySide6.QtCore import Qt, QRect, QSize
from typing import Optional
import cv2
import numpy as np


class ScalableVideoLabel(QWidget):
    """
    Виджет для отображения видео с автоматическим масштабированием.
    
    Особенности:
    - Автоматическое масштабирование с сохранением пропорций
    - Центрирование изображения в виджете
    - Эффективная перерисовка при изменении размеров
    - Поддержка OpenCV кадров (BGR -> RGB конвертацию)
    """
    
    def __init__(self, parent: Optional[QWidget] = None):
        """
        Инициализация виджета.
        
        Args:
            parent: Родительский виджет
        """
        super().__init__(parent)
        
        # Текущий кадр в формате QPixmap
        self._current_pixmap: Optional[QPixmap] = None
        
        # Масштабированный и центрированный pixmap для отрисовки
        self._scaled_pixmap: Optional[QPixmap] = None
        
        # Геометрия отрисовки (позиция и размер в виджете)
        self._pixmap_rect: Optional[QRect] = None
        
        # Флаг необходимости перерасчета масштабирования
        self._needs_scaling_update: bool = True
        
        # Настройки виджета
        self.setMinimumSize(320, 180)  # Минимальный размер
        self.setStyleSheet("background-color: black;")  # Фон - черный
        
    def set_frame(self, frame) -> None:
        """
        Установить новый кадр для отображения.
        
        Args:
            frame: OpenCV кадр (numpy array в формате BGR)
        """
        if frame is None:
            self._current_pixmap = None
            self._scaled_pixmap = None
            self._pixmap_rect = None
            self._needs_scaling_update = True
            self.update()
            return
            
        try:
            # Конвертация BGR -> RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            
            # Создание QImage и QPixmap
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self._current_pixmap = QPixmap.fromImage(qt_image)
            
            # Помечаем, что нужно пересчитать масштабирование
            self._needs_scaling_update = True
            self.update()
            
        except Exception as e:
            # В случае ошибки очищаем изображение
            self._current_pixmap = None
            self._scaled_pixmap = None
            self._pixmap_rect = None
            self._needs_scaling_update = True
            self.update()
    
    def setPixmap(self, pixmap: QPixmap) -> None:
        """
        Установить QPixmap напрямую (для совместимости с QLabel).
        
        Args:
            pixmap: QPixmap для отображения
        """
        self._current_pixmap = pixmap
        self._needs_scaling_update = True
        self.update()
    
    def pixmap(self) -> Optional[QPixmap]:
        """
        Получить текущий pixmap.
        
        Returns:
            Текущий QPixmap или None
        """
        return self._current_pixmap
    
    def clear(self) -> None:
        """
        Очистить отображаемое изображение.
        """
        self._current_pixmap = None
        self._scaled_pixmap = None
        self._pixmap_rect = None
        self._needs_scaling_update = True
        self.update()
    
    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Обработка изменения размера виджета.
        Пересчитываем масштабирование при изменении размеров.
        """
        super().resizeEvent(event)
        self._needs_scaling_update = True
        self.update()
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Обработка события перерисовки.
        Отрисовывает изображение с автоматическим масштабированием и центрированием.
        """
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Если нет изображения - рисуем фон
        if self._current_pixmap is None or self._current_pixmap.isNull():
            painter.fillRect(self.rect(), Qt.GlobalColor.black)
            return
        
        # Пересчитываем масштабирование при необходимости
        if self._needs_scaling_update:
            self._update_scaling()
            self._needs_scaling_update = False
        
        # Рисуем масштабированное изображение
        if self._scaled_pixmap and not self._scaled_pixmap.isNull() and self._pixmap_rect:
            painter.drawPixmap(self._pixmap_rect, self._scaled_pixmap)
    
    def _update_scaling(self) -> None:
        """
        Пересчитать масштабирование и позицию изображения.
        """
        if not self._current_pixmap or self._current_pixmap.isNull():
            self._scaled_pixmap = None
            self._pixmap_rect = None
            return
        
        # Размеры виджета
        widget_width = self.width()
        widget_height = self.height()
        
        # Размеры исходного изображения
        pixmap_width = self._current_pixmap.width()
        pixmap_height = self._current_pixmap.height()
        
        # Вычисляем масштаб с сохранением пропорций
        scale_width = widget_width / pixmap_width
        scale_height = widget_height / pixmap_height
        scale = min(scale_width, scale_height)
        
        # Вычисляем размеры масштабированного изображения
        scaled_width = int(pixmap_width * scale)
        scaled_height = int(pixmap_height * scale)
        
        # Центрируем изображение
        x = (widget_width - scaled_width) // 2
        y = (widget_height - scaled_height) // 2
        
        # Создаем масштабированный pixmap
        self._scaled_pixmap = self._current_pixmap.scaled(
            scaled_width, scaled_height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Сохраняем геометрию для отрисовки
        self._pixmap_rect = QRect(x, y, scaled_width, scaled_height)
    
    def sizeHint(self) -> QSize:
        """
        Возвращает предпочтительный размер виджета.
        """
        if self._current_pixmap and not self._current_pixmap.isNull():
            return self._current_pixmap.size()
        return QSize(640, 360)  # Размер по умолчанию
    
    def minimumSizeHint(self) -> QSize:
        """
        Возвращает минимальный размер виджета.
        """
        return QSize(320, 180)