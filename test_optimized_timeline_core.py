#!/usr/bin/env python3
"""
Тест оптимизированного обновления таймлайна без ObservableMarker (без GUI).

Проверяет работу TimelineController.update_marker_optimized() без зависимостей от виджетов.
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch

# Добавляем src в путь для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from models.domain.marker import Marker
    from models.domain.project import Project
    from models.config.app_settings import AppSettings
    from services.history import HistoryManager
    from controllers.timeline_controller import TimelineController
except ImportError as e:
    print(f"Ошибка импорта: {e}")
    print("Проверьте структуру проекта и наличие файлов")
    sys.exit(1)


class TestOptimizedTimelineCore(unittest.TestCase):
    """Тесты для оптимизированного обновления таймлайна (без GUI)."""

    def setUp(self):
        """Настройка теста."""
        # Создаем проект
        self.project = Project("Test Project")
        self.project.markers = [
            Marker(100, 200, "Event A", "Test note 1"),
            Marker(300, 400, "Event B", "Test note 2"),
            Marker(500, 600, "Event A", "Test note 3")
        ]

        # Создаем настройки
        self.settings = AppSettings()
        self.settings.recording_mode = "dynamic"
        self.settings.pre_roll_sec = 0.0
        self.settings.post_roll_sec = 0.0
        self.settings.fixed_duration_sec = 5.0

        # Создаем history manager
        self.history_manager = HistoryManager()

        # Создаем mock для timeline widget
        self.timeline_widget = Mock()

        # Создаем mock для segment list widget
        self.segment_list_widget = Mock()

        # Создаем контроллер
        self.controller = TimelineController(
            self.project,
            self.timeline_widget,
            self.segment_list_widget,
            self.history_manager,
            self.settings
        )

        # Устанавливаем параметры видео
        self.controller.set_fps(30.0)
        self.controller.set_total_frames(1000)

    def test_update_marker_optimized(self):
        """Тест оптимизированного обновления маркера."""
        # Проверяем начальное состояние
        initial_marker = self.project.markers[0]
        self.assertEqual(initial_marker.start_frame, 100)
        self.assertEqual(initial_marker.end_frame, 200)
        self.assertEqual(initial_marker.event_name, "Event A")

        # Подключаем сигнал для проверки оптимизированного обновления
        update_called = False
        def on_marker_updated(index):
            nonlocal update_called
            update_called = True
            self.assertEqual(index, 0)  # Должен быть индекс обновленного маркера

        self.controller.marker_updated.connect(on_marker_updated)

        # Выполняем оптимизированное обновление
        self.controller.update_marker_optimized(0, 150, 250, "Event C", "Updated note")

        # Проверяем изменения
        updated_marker = self.project.markers[0]
        self.assertEqual(updated_marker.start_frame, 150)
        self.assertEqual(updated_marker.end_frame, 250)
        self.assertEqual(updated_marker.event_name, "Event C")
        self.assertEqual(updated_marker.note, "Updated note")

        # Проверяем, что был вызван сигнал оптимизированного обновления
        self.assertTrue(update_called, "Сигнал marker_updated должен быть вызван")

        # Проверяем, что команда добавлена в историю
        self.assertEqual(len(self.history_manager.undo_stack), 1)

    def test_update_marker_optimized_invalid_index(self):
        """Тест оптимизированного обновления с неверным индексом."""
        initial_count = len(self.project.markers)

        # Пытаемся обновить маркер с несуществующим индексом
        self.controller.update_marker_optimized(999, 150, 250, "Event C", "Updated note")

        # Проверяем, что маркеры не изменились
        self.assertEqual(len(self.project.markers), initial_count)

        # Проверяем, что история не изменилась
        self.assertEqual(len(self.history_manager.undo_stack), 0)

    def test_update_marker_optimized_partial_update(self):
        """Тест частичного обновления маркера (только временные метки)."""
        initial_marker = self.project.markers[1]
        initial_event = initial_marker.event_name
        initial_note = initial_marker.note

        # Обновляем только временные метки
        self.controller.update_marker_optimized(1, 350, 450)

        # Проверяем изменения
        updated_marker = self.project.markers[1]
        self.assertEqual(updated_marker.start_frame, 350)
        self.assertEqual(updated_marker.end_frame, 450)
        self.assertEqual(updated_marker.event_name, initial_event)  # Не должно измениться
        self.assertEqual(updated_marker.note, initial_note)  # Не должно измениться

    def test_update_marker_optimized_event_only(self):
        """Тест обновления только типа события."""
        initial_marker = self.project.markers[2]
        initial_start = initial_marker.start_frame
        initial_end = initial_marker.end_frame
        initial_note = initial_marker.note

        # Обновляем только тип события
        self.controller.update_marker_optimized(2, initial_start, initial_end, "Event D")

        # Проверяем изменения
        updated_marker = self.project.markers[2]
        self.assertEqual(updated_marker.start_frame, initial_start)
        self.assertEqual(updated_marker.end_frame, initial_end)
        self.assertEqual(updated_marker.event_name, "Event D")
        self.assertEqual(updated_marker.note, initial_note)  # Не должно измениться

    def test_optimized_update_preserves_history(self):
        """Тест, что оптимизированное обновление сохраняет историю команд."""
        # Выполняем несколько оптимизированных обновлений
        self.controller.update_marker_optimized(0, 150, 250, "Event C", "Note 1")
        self.controller.update_marker_optimized(1, 350, 450, "Event D", "Note 2")
        self.controller.update_marker_optimized(2, 550, 650, "Event E", "Note 3")

        # Проверяем, что все команды добавлены в историю
        self.assertEqual(len(self.history_manager.undo_stack), 3)

        # Проверяем возможность отмены
        self.history_manager.undo()
        self.assertEqual(len(self.history_manager.undo_stack), 2)
        self.assertEqual(len(self.history_manager.redo_stack), 1)

        # Проверяем возможность повтора
        self.history_manager.redo()
        self.assertEqual(len(self.history_manager.undo_stack), 3)
        self.assertEqual(len(self.history_manager.redo_stack), 0)

    def test_optimized_update_signals(self):
        """Тест сигналов оптимизированного обновления."""
        # Подключаем сигналы
        markers_changed_called = False
        marker_updated_called = False
        project_modified_called = False

        def on_markers_changed():
            nonlocal markers_changed_called
            markers_changed_called = True

        def on_marker_updated(index):
            nonlocal marker_updated_called
            marker_updated_called = True
            self.assertEqual(index, 1)

        def on_project_modified():
            nonlocal project_modified_called
            project_modified_called = True

        self.controller.markers_changed.connect(on_markers_changed)
        self.controller.marker_updated.connect(on_marker_updated)
        self.controller.project_modified.connect(on_project_modified)

        # Выполняем оптимизированное обновление
        self.controller.update_marker_optimized(1, 350, 450, "Event D", "Updated note")

        # Проверяем, что сигналы были вызваны
        # markers_changed не должен вызываться при оптимизированном обновлении
        self.assertFalse(markers_changed_called, "Сигнал markers_changed не должен быть вызван при оптимизированном обновлении")
        self.assertTrue(marker_updated_called, "Сигнал marker_updated должен быть вызван")
        self.assertTrue(project_modified_called, "Сигнал project_modified должен быть вызван")


def run_tests():
    """Запуск тестов."""
    print("Запуск тестов оптимизированного обновления таймлайна (без GUI)...")

    # Создаем тестовый набор
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestOptimizedTimelineCore)

    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Выводим результаты
    if result.wasSuccessful():
        print("\n✅ Все тесты пройдены успешно!")
        print(f"Выполнено тестов: {result.testsRun}")
        return True
    else:
        print(f"\n❌ Тесты не пройдены!")
        print(f"Выполнено тестов: {result.testsRun}")
        print(f"Ошибки: {len(result.errors)}")
        print(f"Сбои: {len(result.failures)}")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)