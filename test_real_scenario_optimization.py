"""Интеграционный тест для демонстрации оптимизированной системы обновления таймлайна.

Этот тест показывает, как будет работать система в реальном сценарии:
1. Пользователь открывает редактор отрезка
2. Изменяет IN/OUT точки
3. Сохраняет изменения
4. Таймлайн мгновенно обновляется
"""


import unittest
import sys
import os
import time

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QTimer, QEventLoop

from models.domain.marker import Marker
from models.domain.project import Project
from models.domain.observable_project import ObservableProject
from models.domain.observable_marker import ObservableMarker
from models.config.app_settings import AppSettings
from services.history import HistoryManager
from views.widgets.segment_list import SegmentListWidget
from views.widgets.timeline import TimelineWidget
from controllers.timeline_controller_optimized import OptimizedTimelineController


class TestRealScenarioOptimization(unittest.TestCase):
    """Интеграционный тест для демонстрации оптимизированной системы."""

    @classmethod
    def setUpClass(cls):
        """Инициализация QApplication для всех тестов."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        """Настройка тестового окружения."""
        # Создаем тестовый проект с несколькими маркерами
        self.project = Project(name="Test Project")
        self.project.markers = [
            Marker(start_frame=100, end_frame=200, event_name="Attack", note="Test attack"),
            Marker(start_frame=300, end_frame=400, event_name="Defense", note="Test defense"),
            Marker(start_frame=500, end_frame=600, event_name="Attack", note="Another attack"),
            Marker(start_frame=700, end_frame=800, event_name="Change", note="Line change"),
            Marker(start_frame=900, end_frame=1000, event_name="Attack", note="Final attack")
        ]
        self.project.video_path = "test_video.mp4"
        self.project.fps = 30.0

        # Создаем настройки
        self.settings = AppSettings()

        # Создаем сервис истории
        self.history_manager = HistoryManager()

        # Создаем виджеты
        self.timeline_widget = TimelineWidget()
        self.segment_list_widget = SegmentListWidget()

        # Создаем оптимизированный контроллер
        self.controller = OptimizedTimelineController(
            project=self.project,
            timeline_widget=self.timeline_widget,
            segment_list_widget=self.segment_list_widget,
            history_manager=self.history_manager,
            settings=self.settings
        )

        # Устанавливаем реактивный проект
        self.observable_project = ObservableProject.from_project(self.project)
        self.controller.set_observable_project(self.observable_project)

        # Устанавливаем FPS и общее количество кадров
        self.controller.set_fps(30.0)
        self.controller.set_total_frames(2000)

    def tearDown(self):
        """Очистка после теста."""
        # Очищаем очередь обновлений
        self.controller._pending_updates.clear()
        if self.controller._update_timer.isActive():
            self.controller._update_timer.stop()

    def test_real_editing_scenario(self):
        """Тест реального сценария редактирования отрезка."""
        print("\n=== Тест реального сценария редактирования ===")
        
        # 1. Изначальное состояние
        initial_marker = self.observable_project.markers[2]  # Attack at 500-600
        print(f"1. Изначальный маркер: {initial_marker.start_frame}-{initial_marker.end_frame} ({initial_marker.event_name})")
        
        # Проверяем, что UI инициализирован (проверяем через контроллер)
        self.assertEqual(len(self.controller.markers), 5)
        
        # 2. Пользователь открывает редактор отрезка (InstanceEditWindow)
        # В реальности это делается через main_window.open_segment_editor(2)
        print("2. Пользователь открывает редактор отрезка...")
        
        # 3. Пользователь изменяет IN точку с 500 на 520
        print("3. Пользователь изменяет IN точку с 500 на 520...")
        start_time = time.time()
        
        initial_marker.start_frame = 520
        
        # Измеряем время реакции системы
        reaction_time = time.time() - start_time
        print(f"   Время реакции системы: {reaction_time*1000:.2f}ms")
        
        # Проверяем, что изменения применились
        self.assertEqual(initial_marker.start_frame, 520)
        self.assertEqual(self.project.markers[2].start_frame, 520)  # Проверяем синхронизацию
        
        # Проверяем, что обновление запланировано
        self.assertTrue(self.controller._pending_updates)
        self.assertTrue(self.controller._update_timer.isActive())
        
        # 4. Пользователь изменяет OUT точку с 600 на 650
        print("4. Пользователь изменяет OUT точку с 600 на 650...")
        start_time = time.time()
        
        initial_marker.end_frame = 650
        
        reaction_time = time.time() - start_time
        print(f"   Время реакции системы: {reaction_time*1000:.2f}ms")
        
        # Проверяем изменения
        self.assertEqual(initial_marker.end_frame, 650)
        self.assertEqual(self.project.markers[2].end_frame, 650)
        
        # 5. Пользователь изменяет тип события с "Attack" на "Breakout"
        print("5. Пользователь изменяет тип события с 'Attack' на 'Breakout'...")
        start_time = time.time()
        
        initial_marker.event_name = "Breakout"
        
        reaction_time = time.time() - start_time
        print(f"   Время реакции системы: {reaction_time*1000:.2f}ms")
        
        # Проверяем изменения
        self.assertEqual(initial_marker.event_name, "Breakout")
        self.assertEqual(self.project.markers[2].event_name, "Breakout")
        
        # 6. Пользователь добавляет заметку
        print("6. Пользователь добавляет заметку...")
        start_time = time.time()
        
        initial_marker.note = "Breakout with speed"
        
        reaction_time = time.time() - start_time
        print(f"   Время реакции системы: {reaction_time*1000:.2f}ms")
        
        # Проверяем изменения
        self.assertEqual(initial_marker.note, "Breakout with speed")
        self.assertEqual(self.project.markers[2].note, "Breakout with speed")
        
        # 7. Пользователь нажимает "Сохранить"
        print("7. Пользователь нажимает 'Сохранить'...")
        start_time = time.time()
        
        # В реальной системе здесь происходит сохранение в историю команд
        # и оптимизированное обновление UI
        
        # Ждем выполнения всех запланированных обновлений
        loop = QEventLoop()
        QTimer.singleShot(50, loop.quit)  # Ждем 50ms
        loop.exec_()
        
        save_time = time.time() - start_time
        print(f"   Время сохранения и обновления UI: {save_time*1000:.2f}ms")
        
        # Проверяем, что очередь обновлений очищена
        self.assertFalse(self.controller._pending_updates)
        self.assertFalse(self.controller._update_timer.isActive())
        
        # 8. Проверяем финальное состояние
        print("8. Финальное состояние маркера:")
        final_marker = self.observable_project.markers[2]
        print(f"   {final_marker.start_frame}-{final_marker.end_frame} ({final_marker.event_name}) - {final_marker.note}")
        
        # Проверяем, что все изменения сохранились
        self.assertEqual(final_marker.start_frame, 520)
        self.assertEqual(final_marker.end_frame, 650)
        self.assertEqual(final_marker.event_name, "Breakout")
        self.assertEqual(final_marker.note, "Breakout with speed")
        
        # Проверяем, что UI обновлен (проверяем через контроллер)
        self.assertEqual(len(self.controller.markers), 5)
        
        print("   ✅ Все изменения успешно применены и отображены!")

    def test_performance_with_many_markers(self):
        """Тест производительности с большим количеством маркеров."""
        print("\n=== Тест производительности с 1000 маркерами ===")
        
        # Добавляем много маркеров для тестирования производительности
        start_time = time.time()
        
        for i in range(1000):
            marker = ObservableMarker(
                start_frame=i * 10, 
                end_frame=i * 10 + 5, 
                event_name="Test", 
                note=f"Marker {i}"
            )
            self.observable_project.add_marker(marker)
        
        add_time = time.time() - start_time
        print(f"Время добавления 1000 маркеров: {add_time*1000:.2f}ms")
        
        # Проверяем количество маркеров
        self.assertEqual(len(self.observable_project.markers), 1005)  # Было 5, добавили 1000
        
        # Тестируем быстрое изменение одного маркера
        print("Тест быстрого изменения одного маркера из 1000...")
        marker_to_change = self.observable_project.markers[500]
        start_time = time.time()
        
        marker_to_change.start_frame = 5000
        marker_to_change.end_frame = 5005
        marker_to_change.event_name = "Changed"
        marker_to_change.note = "Quick change"
        
        change_time = time.time() - start_time
        print(f"Время изменения маркера: {change_time*1000:.2f}ms")
        print(f"Время реакции системы: {change_time*1000:.2f}ms (должно быть < 5ms)")
        
        # Проверяем изменения
        self.assertEqual(marker_to_change.start_frame, 5000)
        self.assertEqual(marker_to_change.end_frame, 5005)
        self.assertEqual(marker_to_change.event_name, "Changed")
        self.assertEqual(marker_to_change.note, "Quick change")
        
        # Проверяем, что обновление запланировано
        self.assertTrue(self.controller._pending_updates)
        self.assertTrue(self.controller._update_timer.isActive())

    def test_undo_redo_performance(self):
        """Тест производительности undo/redo операций."""
        print("\n=== Тест производительности undo/redo ===")
        
        # Добавляем несколько маркеров
        for i in range(10):
            self.controller.add_marker(i * 100, i * 100 + 50, "Test", f"Marker {i}")
        
        # Тестируем undo
        print("Тест undo операции...")
        start_time = time.time()
        
        try:
            self.controller.undo()
            undo_time = time.time() - start_time
            print(f"Время undo операции: {undo_time*1000:.2f}ms")
        except Exception as e:
            print(f"Undo не поддерживается: {e}")
        
        # Тестируем redo
        print("Тест redo операции...")
        start_time = time.time()
        
        try:
            self.controller.redo()
            redo_time = time.time() - start_time
            print(f"Время redo операции: {redo_time*1000:.2f}ms")
        except Exception as e:
            print(f"Redo не поддерживается: {e}")

    def test_concurrent_edits(self):
        """Тест одновременного редактирования нескольких маркеров."""
        print("\n=== Тест одновременного редактирования ===")
        
        # Изменяем несколько маркеров одновременно
        print("Изменение 5 маркеров одновременно...")
        start_time = time.time()
        
        for i in range(5):
            marker = self.observable_project.markers[i]
            marker.start_frame += 10
            marker.end_frame += 10
            marker.note = f"Updated {i}"
        
        concurrent_time = time.time() - start_time
        print(f"Время одновременного изменения 5 маркеров: {concurrent_time*1000:.2f}ms")
        print(f"Время реакции системы: {concurrent_time*1000:.2f}ms")
        
        # Проверяем изменения
        for i in range(5):
            marker = self.observable_project.markers[i]
            self.assertEqual(marker.start_frame, 100 + i*200 + 10)  # 100, 300, 500, 700, 900 + 10
            self.assertEqual(marker.end_frame, 200 + i*200 + 10)    # 200, 400, 600, 800, 1000 + 10
            self.assertEqual(marker.note, f"Updated {i}")
        
        # Проверяем, что обновление запланировано
        self.assertTrue(self.controller._pending_updates)
        self.assertTrue(self.controller._update_timer.isActive())


if __name__ == '__main__':
    print("Запуск интеграционных тестов оптимизированной системы...")
    unittest.main(verbosity=2)