#!/usr/bin/env python3
"""
Тест для проверки функциональности удаления сегментов клавишей Delete.

Этот тест проверяет:
1. Регистрацию глобального shortcut для Delete
2. Передачу сигнала от ShortcutController к MainController
3. Вызов метода удаления сегмента
4. Работу команды удаления в TimelineController
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch

# Добавляем путь к src для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

# Импортируем компоненты для тестирования
from controllers.shortcut_controller import ShortcutController
from controllers.main_controller import MainController
from controllers.timeline_controller import TimelineController
from models.domain.project import Project
from models.domain.marker import Marker
from models.config.app_settings import AppSettings
from services.history import HistoryManager
from views.widgets.segment_list import SegmentListWidget
from views.widgets.timeline_scene import TimelineWidget


class TestDeleteFunctionality(unittest.TestCase):
    """Тесты для функциональности удаления сегментов."""
    
    def setUp(self):
        """Настройка тестового окружения."""
        # Создаем QApplication для тестов
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
        
        # Создаем mock объекты
        self.mock_parent_window = Mock()
        self.mock_timeline_widget = Mock()
        self.mock_segment_list_widget = Mock()
        
        # Создаем компоненты
        self.project = Project(name="Test Project")
        self.settings = AppSettings()
        self.history_manager = HistoryManager()
        
        # Создаем маркеры для тестирования
        self.marker1 = Marker(id=1, start_frame=100, end_frame=200, event_name="Test Event 1")
        self.marker2 = Marker(id=2, start_frame=300, end_frame=400, event_name="Test Event 2")
        self.project.add_marker(self.marker1)
        self.project.add_marker(self.marker2)
        
        # Создаем контроллеры
        self.timeline_controller = TimelineController(
            self.project,
            self.mock_timeline_widget,
            self.mock_segment_list_widget,
            self.history_manager,
            self.settings
        )
        
        self.shortcut_controller = ShortcutController(self.mock_parent_window)
        
        # Подключаем сигналы
        self.shortcut_controller.shortcut_pressed.connect(self._on_shortcut_received)
        self.received_shortcut = None
    
    def _on_shortcut_received(self, key):
        """Обработчик полученного сигнала."""
        self.received_shortcut = key
    
    def test_delete_shortcut_registration(self):
        """Тест регистрации shortcut для Delete."""
        print("Тест: Регистрация shortcut для Delete")
        
        # Проверяем, что shortcut для Delete зарегистрирован
        delete_shortcut = self.shortcut_controller.shortcut_manager.get_shortcut('DELETE')
        self.assertIsNotNone(delete_shortcut, "Delete shortcut should be registered")
        
        print("✓ Delete shortcut успешно зарегистрирован")
    
    def test_delete_shortcut_activation(self):
        """Тест активации shortcut для Delete."""
        print("Тест: Активация shortcut для Delete")
        
        # Имитируем нажатие Delete
        self.shortcut_controller._on_global_shortcut_activated('DELETE')
        
        # Проверяем, что сигнал был получен
        self.assertEqual(self.received_shortcut, 'DELETE', "Should receive DELETE signal")
        
        print("✓ Delete shortcut успешно активирован")
    
    def test_timeline_controller_delete_marker(self):
        """Тест удаления маркера в TimelineController."""
        print("Тест: Удаление маркера в TimelineController")
        
        # Проверяем начальное количество маркеров
        initial_count = len(self.project.markers)
        self.assertEqual(initial_count, 2, "Should have 2 markers initially")
        
        # Удаляем первый маркер
        self.timeline_controller.delete_marker(0)
        
        # Проверяем, что маркер удален
        final_count = len(self.project.markers)
        self.assertEqual(final_count, 1, "Should have 1 marker after deletion")
        self.assertEqual(self.project.markers[0].id, 2, "Remaining marker should be marker2")
        
        print("✓ Маркер успешно удален из TimelineController")
    
    def test_delete_marker_command(self):
        """Тест команды удаления маркера."""
        print("Тест: Команда удаления маркера")
        
        # Создаем команду удаления
        marker = self.project.markers[0]
        command = self.timeline_controller.DeleteMarkerCommand(self.project, marker)
        
        # Выполняем команду
        command.execute()
        
        # Проверяем, что маркер удален
        self.assertEqual(len(self.project.markers), 1, "Marker should be deleted")
        
        # Отменяем команду
        command.undo()
        
        # Проверяем, что маркер восстановлен
        self.assertEqual(len(self.project.markers), 2, "Marker should be restored")
        
        print("✓ Команда удаления маркера работает корректно")
    
    def test_delete_with_empty_project(self):
        """Тест удаления из пустого проекта."""
        print("Тест: Удаление из пустого проекта")
        
        # Очищаем проект
        self.project.markers.clear()
        
        # Пытаемся удалить маркер из пустого проекта
        self.timeline_controller.delete_marker(0)
        
        # Проверяем, что ничего не сломалось
        self.assertEqual(len(self.project.markers), 0, "Project should remain empty")
        
        print("✓ Удаление из пустого проекта обработано корректно")
    
    def test_delete_invalid_index(self):
        """Тест удаления с неверным индексом."""
        print("Тест: Удаление с неверным индексом")
        
        # Пытаемся удалить маркер с неверным индексом
        self.timeline_controller.delete_marker(999)
        
        # Проверяем, что ничего не сломалось
        self.assertEqual(len(self.project.markers), 2, "Project should remain unchanged")
        
        print("✓ Удаление с неверным индексом обработано корректно")
    
    def test_selected_markers_functionality(self):
        """Тест функциональности выделенных маркеров."""
        print("Тест: Функциональность выделенных маркеров")
        
        # Выделяем первый маркер
        self.timeline_controller.select_marker(0)
        
        # Проверяем, что маркер выделен
        selected = self.timeline_controller.get_selected_markers()
        self.assertEqual(selected, [0], "First marker should be selected")
        
        # Снимаем выделение
        self.timeline_controller.deselect_marker(0)
        
        # Проверяем, что выделение снято
        selected = self.timeline_controller.get_selected_markers()
        self.assertEqual(selected, [], "No markers should be selected")
        
        # Выделяем несколько маркеров
        self.timeline_controller.select_marker(0)
        self.timeline_controller.select_marker(1)
        
        # Проверяем выделение
        selected = self.timeline_controller.get_selected_markers()
        self.assertEqual(set(selected), {0, 1}, "Both markers should be selected")
        
        print("✓ Функциональность выделенных маркеров работает корректно")


def run_tests():
    """Запуск всех тестов."""
    print("Запуск тестов функциональности Delete...")
    print("=" * 50)
    
    # Создаем тест-сью
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDeleteFunctionality)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 50)
    if result.wasSuccessful():
        print("✅ Все тесты пройдены! Функциональность Delete работает корректно.")
    else:
        print("❌ Некоторые тесты не прошли. Проверьте реализацию.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)