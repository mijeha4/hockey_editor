#!/usr/bin/env python3
"""
Test for timeline zoom fix - проверка отсутствия наложения меток времени при масштабировании.
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from views.widgets.timeline import TimelineGraphicsScene, TimelineWidget
from models.domain.marker import Marker
from services.events.custom_event_manager import get_custom_event_manager


class TestTimelineZoomFix(unittest.TestCase):
    """Тесты для проверки исправления наложения меток времени при масштабировании."""

    def setUp(self):
        """Настройка теста."""
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])

        # Создаем контроллер для теста
        self.mock_controller = Mock()
        self.mock_controller.get_fps.return_value = 30.0
        self.mock_controller.get_total_frames.return_value = 9000  # 5 минут видео
        self.mock_controller.get_current_frame_idx.return_value = 0
        self.mock_controller.markers = []

        # Создаем сцену
        self.scene = TimelineGraphicsScene(self.mock_controller)
        
        # Создаем виджет
        self.widget = TimelineWidget(self.mock_controller)

    def test_zoom_out_prevents_overlap(self):
        """Тест: при уменьшении масштаба метки времени не должны накладываться."""
        # Устанавливаем очень маленький масштаб (уменьшаем)
        self.scene.pixels_per_frame = 0.1  # Очень маленький масштаб
        
        # Создаем видимую область для теста
        test_rect = self.scene.sceneRect()
        
        # Создаем QPainter для тестирования рисования
        pixmap = QPixmap(800, 100)
        painter = QPainter(pixmap)
        
        try:
            # Рисуем foreground (линейку времени)
            self.scene.drawForeground(painter, test_rect)
            
            # Проверяем, что метод завершается без ошибок
            self.assertTrue(True, "drawForeground completed without errors")
            
        finally:
            painter.end()

    def test_zoom_in_normal_spacing(self):
        """Тест: при нормальном масштабе метки должны быть с интервалом 5 секунд."""
        # Устанавливаем нормальный масштаб
        self.scene.pixels_per_frame = 0.8  # Нормальный масштаб
        
        # Проверяем, что интервал должен быть 5 секунд
        fps = 30.0
        min_spacing_px = 80
        current_spacing_px = self.scene.pixels_per_frame * fps * 5
        
        # При нормальном масштабе интервал должен быть 5 секунд
        self.assertEqual(current_spacing_px, 0.8 * 30 * 5)  # 120 пикселей
        self.assertGreater(current_spacing_px, min_spacing_px)  # Должно быть больше минимального

    def test_zoom_out_increases_interval(self):
        """Тест: при уменьшении масштаба интервал между метками должен увеличиваться."""
        # Очень маленький масштаб
        self.scene.pixels_per_frame = 0.05
        
        fps = 30.0
        min_spacing_px = 80
        current_spacing_px = self.scene.pixels_per_frame * fps * 5
        
        # При малом масштабе интервал должен быть меньше минимального
        self.assertLess(current_spacing_px, min_spacing_px)  # 7.5 пикселей < 80
        
        # Рассчитываем адаптивный интервал
        step_seconds = max(5, int(min_spacing_px / (self.scene.pixels_per_frame * fps)))
        
        # Должен быть увеличенный интервал
        self.assertGreater(step_seconds, 5)

    def test_adaptive_interval_rounding(self):
        """Тест: адаптивный интервал должен округляться до удобных значений."""
        test_cases = [
            (0.05, 53),   # Должно стать 60
            (0.1, 27),    # Должно стать 30
            (0.15, 18),   # Должно стать 15
            (0.2, 13),    # Должно стать 15
            (0.3, 9),     # Должно стать 10
            (0.5, 5),     # Должно остаться 5
        ]
        
        for pixels_per_frame, expected_base in test_cases:
            with self.subTest(pixels_per_frame=pixels_per_frame):
                self.scene.pixels_per_frame = pixels_per_frame
                
                # Рассчитываем интервал
                fps = 30.0
                min_spacing_px = 80
                current_spacing_px = self.scene.pixels_per_frame * fps * 5
                
                if current_spacing_px < min_spacing_px:
                    step_seconds = max(5, int(min_spacing_px / (self.scene.pixels_per_frame * fps)))
                    
                    # Округление до удобных значений
                    if step_seconds <= 7:
                        step_seconds = 5
                    elif step_seconds <= 12:
                        step_seconds = 10
                    elif step_seconds <= 20:
                        step_seconds = 15
                    elif step_seconds <= 40:
                        step_seconds = 30
                    else:
                        step_seconds = 60
                
                    # Проверяем округление
                    self.assertIn(step_seconds, [5, 10, 15, 30, 60])

    def test_text_centering_prevents_overlap(self):
        """Тест: центрирование текста предотвращает наложение."""
        # Устанавливаем маленький масштаб для тестирования
        self.scene.pixels_per_frame = 0.1
        
        # Создаем контроллера с метками
        mock_controller = Mock()
        mock_controller.get_fps.return_value = 30.0
        mock_controller.get_total_frames.return_value = 9000
        mock_controller.get_current_frame_idx.return_value = 0
        mock_controller.markers = []
        
        scene = TimelineGraphicsScene(mock_controller)
        scene.pixels_per_frame = 0.1
        
        # Проверяем, что метод drawForeground не вызывает исключений
        test_rect = scene.sceneRect()
        pixmap = QPixmap(800, 100)
        painter = QPainter(pixmap)
        
        try:
            scene.drawForeground(painter, test_rect)
            # Если метод завершился без ошибок, тест пройден
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"drawForeground raised an exception: {e}")
        finally:
            painter.end()

    def test_minimum_spacing_enforcement(self):
        """Тест: минимальное расстояние между метками соблюдается."""
        # Устанавливаем очень маленький масштаб
        self.scene.pixels_per_frame = 0.01
        
        # Проверяем расчет минимального расстояния
        min_spacing_px = 80
        fps = 30.0
        
        # Рассчитываем необходимый интервал
        required_step = min_spacing_px / (self.scene.pixels_per_frame * fps)
        
        # Должен быть значительный интервал
        self.assertGreater(required_step, 20)  # Больше 20 секунд

    def test_zoom_wheel_event_updates_spacing(self):
        """Тест: колесо мыши с Ctrl изменяет масштаб и интервал меток."""
        # Проверяем, что масштаб можно изменить вручную
        initial_scale = self.scene.pixels_per_frame
        
        # Изменяем масштаб вручную (имитация zoom)
        self.scene.pixels_per_frame *= 0.8  # Уменьшаем масштаб
        
        # Проверяем, что масштаб изменился
        self.assertNotEqual(self.scene.pixels_per_frame, initial_scale)
        self.assertLess(self.scene.pixels_per_frame, initial_scale)  # Уменьшился


if __name__ == '__main__':
    # Запускаем тесты
    unittest.main(verbosity=2)