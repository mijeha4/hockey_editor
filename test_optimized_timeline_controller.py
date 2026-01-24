"""Тесты для оптимизированного TimelineController с реактивными моделями."""

import unittest
import sys
import os

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


class TestOptimizedTimelineController(unittest.TestCase):
    """Тесты для оптимизированного TimelineController."""

    @classmethod
    def setUpClass(cls):
        """Инициализация QApplication для всех тестов."""
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        """Настройка тестового окружения."""
        # Создаем тестовый проект
        self.project = Project(name="Test Project")
        self.project.markers = [
            Marker(start_frame=100, end_frame=200, event_name="Attack", note="Test attack"),
            Marker(start_frame=300, end_frame=400, event_name="Defense", note="Test defense"),
            Marker(start_frame=500, end_frame=600, event_name="Attack", note="Another attack")
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

        # Создаем контроллер
        self.controller = OptimizedTimelineController(
            project=self.project,
            timeline_widget=self.timeline_widget,
            segment_list_widget=self.segment_list_widget,
            history_manager=self.history_manager,
            settings=self.settings
        )

        # Устанавливаем FPS и общее количество кадров
        self.controller.set_fps(30.0)
        self.controller.set_total_frames(1000)

    def tearDown(self):
        """Очистка после теста."""
        # Очищаем очередь обновлений
        self.controller._pending_updates.clear()
        if self.controller._update_timer.isActive():
            self.controller._update_timer.stop()

    def test_initialization(self):
        """Тест инициализации контроллера."""
        self.assertIsNotNone(self.controller.project)
        self.assertIsNotNone(self.controller.timeline_widget)
        self.assertIsNotNone(self.controller.segment_list_widget)
        self.assertIsNotNone(self.controller.history_manager)
        self.assertIsNotNone(self.controller.settings)
        self.assertEqual(self.controller.project.name, "Test Project")

    def test_add_marker_optimized(self):
        """Тест добавления маркера с оптимизацией."""
        initial_count = len(self.project.markers)
        initial_history_count = len(self.history_manager.undo_stack)

        # Добавляем маркер
        self.controller.add_marker(700, 800, "Change", "Test change")

        # Проверяем, что маркер добавлен
        self.assertEqual(len(self.project.markers), initial_count + 1)
        self.assertEqual(self.project.markers[-1].start_frame, 700)
        self.assertEqual(self.project.markers[-1].end_frame, 800)
        self.assertEqual(self.project.markers[-1].event_name, "Change")
        self.assertEqual(self.project.markers[-1].note, "Test change")

        # Проверяем историю команд
        self.assertEqual(len(self.history_manager.undo_stack), initial_history_count + 1)

        # Проверяем, что обновление запланировано
        self.assertTrue(self.controller._pending_updates)

    def test_modify_marker_optimized(self):
        """Тест модификации маркера с оптимизацией."""
        initial_history_count = len(self.history_manager.undo_stack)

        # Модифицируем первый маркер
        new_marker = Marker(start_frame=150, end_frame=250, event_name="Attack", note="Modified attack")
        self.controller.modify_marker(0, new_marker)

        # Проверяем изменения
        self.assertEqual(self.project.markers[0].start_frame, 150)
        self.assertEqual(self.project.markers[0].end_frame, 250)
        self.assertEqual(self.project.markers[0].note, "Modified attack")

        # Проверяем историю команд
        self.assertEqual(len(self.history_manager.undo_stack), initial_history_count + 1)

        # Проверяем, что обновление запланировано
        self.assertTrue(self.controller._pending_updates)

    def test_delete_marker_optimized(self):
        """Тест удаления маркера с оптимизацией."""
        initial_count = len(self.project.markers)
        initial_history_count = len(self.history_manager.undo_stack)

        # Удаляем первый маркер
        self.controller.delete_marker(0)

        # Проверяем, что маркер удален
        self.assertEqual(len(self.project.markers), initial_count - 1)
        self.assertEqual(self.project.markers[0].start_frame, 300)  # Второй маркер стал первым

        # Проверяем историю команд
        self.assertEqual(len(self.history_manager.undo_stack), initial_history_count + 1)

        # Проверяем, что обновление запланировано
        self.assertTrue(self.controller._pending_updates)

    def test_observable_project_integration(self):
        """Тест интеграции с реактивным проектом."""
        # Создаем реактивный проект
        observable_project = ObservableProject.from_project(self.project)

        # Устанавливаем реактивный проект
        self.controller.set_observable_project(observable_project)

        # Проверяем, что проект установлен
        self.assertEqual(self.controller.observable_project, observable_project)
        self.assertEqual(self.controller.project, observable_project.to_project())

        # Добавляем маркер через реактивный проект
        observable_marker = ObservableMarker(900, 1000, "Test", "Observable test")
        observable_project.add_marker(observable_marker)

        # Проверяем, что маркер добавлен
        self.assertEqual(len(observable_project.markers), 4)  # Было 3, добавили 1
        self.assertEqual(len(self.project.markers), 4)

    def test_update_single_marker(self):
        """Тест оптимизированного обновления одного маркера."""
        # Устанавливаем реактивный проект
        observable_project = ObservableProject.from_project(self.project)
        self.controller.set_observable_project(observable_project)

        # Изменяем первый маркер
        marker = observable_project.markers[0]
        marker.start_frame = 120
        marker.end_frame = 220
        marker.event_name = "ModifiedAttack"
        marker.note = "Modified via observable"

        # Проверяем изменения
        self.assertEqual(marker.start_frame, 120)
        self.assertEqual(marker.end_frame, 220)
        self.assertEqual(marker.event_name, "ModifiedAttack")
        self.assertEqual(marker.note, "Modified via observable")

        # Проверяем, что изменения отразились в обычном проекте
        self.assertEqual(self.project.markers[0].start_frame, 120)
        self.assertEqual(self.project.markers[0].end_frame, 220)

    def test_buffered_updates(self):
        """Тест буферизации нескольких обновлений."""
        # Добавляем несколько маркеров подряд
        self.controller.add_marker(700, 800, "Change", "Test 1")
        self.controller.add_marker(850, 950, "Change", "Test 2")
        self.controller.add_marker(1000, 1100, "Change", "Test 3")

        # Проверяем, что все маркеры добавлены
        self.assertEqual(len(self.project.markers), 6)  # Было 3, добавили 3

        # Проверяем, что обновления буферизированы
        self.assertTrue(self.controller._pending_updates)
        self.assertEqual(len(self.controller._pending_updates), 3)

        # Запускаем таймер для выполнения обновлений
        loop = QEventLoop()
        QTimer.singleShot(50, loop.quit)  # Ждем 50ms
        loop.exec_()

        # Проверяем, что очередь обновлений очищена
        self.assertFalse(self.controller._pending_updates)

    def test_undo_redo_with_optimization(self):
        """Тест undo/redo с оптимизацией обновления UI."""
        initial_count = len(self.project.markers)

        # Добавляем маркер
        self.controller.add_marker(700, 800, "Change", "Test undo/redo")

        # Отменяем
        self.controller.undo()

        # Проверяем, что маркер удален
        self.assertEqual(len(self.project.markers), initial_count)

        # Повторяем
        self.controller.redo()

        # Проверяем, что маркер восстановлен
        self.assertEqual(len(self.project.markers), initial_count + 1)
        self.assertEqual(self.project.markers[-1].start_frame, 700)

    def test_hotkey_handling(self):
        """Тест обработки горячих клавиш."""
        # Устанавливаем режим Dynamic
        self.settings.recording_mode = "dynamic"

        # Первое нажатие (начало записи)
        self.controller.handle_hotkey("A", 100, 30.0)
        self.assertTrue(self.controller.is_recording)
        self.assertEqual(self.controller.recording_start_frame, 100)

        # Второе нажатие (конец записи)
        self.controller.handle_hotkey("A", 200, 30.0)
        self.assertFalse(self.controller.is_recording)
        self.assertIsNone(self.controller.recording_start_frame)

        # Проверяем, что маркер добавлен
        self.assertEqual(len(self.project.markers), 4)  # Было 3, добавили 1

    def test_seek_frame(self):
        """Тест перемотки кадра."""
        # Устанавливаем playback controller
        class MockPlaybackController:
            def __init__(self):
                self.current_frame = 0
                self.seek_calls = []

            def seek_to_frame(self, frame):
                self.current_frame = frame
                self.seek_calls.append(frame)

        mock_playback = MockPlaybackController()
        self.controller.set_playback_controller(mock_playback)

        # Перематываем кадр
        self.controller.seek_frame(150, update_playback=True)

        # Проверяем результаты
        self.assertEqual(self.controller.current_frame, 150)
        self.assertEqual(mock_playback.current_frame, 150)
        self.assertEqual(len(mock_playback.seek_calls), 1)
        self.assertEqual(mock_playback.seek_calls[0], 150)

    def test_timeline_seek_integration(self):
        """Тест интеграции с timeline seek."""
        # Подключаем сигнал seek_requested к контроллеру
        # (в реальном приложении это делается автоматически)

        # Эмулируем клик по таймлайну
        self.controller._on_timeline_seek(250)

        # Проверяем, что кадр установлен
        self.assertEqual(self.controller.current_frame, 250)

    def test_performance_with_many_markers(self):
        """Тест производительности с большим количеством маркеров."""
        # Добавляем много маркеров
        for i in range(100):
            self.controller.add_marker(i * 10, i * 10 + 5, "Test", f"Marker {i}")

        # Проверяем количество маркеров
        self.assertEqual(len(self.project.markers), 103)  # Было 3, добавили 100

        # Проверяем, что история команд работает
        self.assertGreater(len(self.history_manager.undo_stack), 0)

        # Проверяем, что обновления буферизированы
        self.assertTrue(self.controller._pending_updates)

    def test_concurrent_updates_prevention(self):
        """Тест предотвращения рекурсивных обновлений."""
        # Устанавливаем реактивный проект
        observable_project = ObservableProject.from_project(self.project)
        self.controller.set_observable_project(observable_project)

        # Изменяем маркер, что должно вызвать обновление UI
        marker = observable_project.markers[0]
        marker.start_frame = 110

        # Проверяем, что флаг _updating_ui сбрасывается
        self.assertFalse(self.controller._updating_ui)

        # Проверяем, что обновления не накапливаются бесконечно
        self.assertLess(len(self.controller._pending_updates), 10)


if __name__ == '__main__':
    print("Запуск тестов оптимизированного TimelineController...")
    unittest.main(verbosity=2)