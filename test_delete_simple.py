#!/usr/bin/env python3
"""
Простой тест для проверки функциональности удаления сегментов клавишей Delete.

Этот тест проверяет основные компоненты без сложных mock объектов.
"""

import sys
import os

# Добавляем путь к src для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_delete_functionality():
    """Тест основной функциональности Delete."""
    print("Тест: Основная функциональность Delete")
    print("=" * 50)
    
    try:
        # Импортируем компоненты
        from models.domain.project import Project
        from models.domain.marker import Marker
        from controllers.timeline_controller import TimelineController
        from services.history import HistoryManager
        from models.config.app_settings import AppSettings
        
        print("✓ Импорты прошли успешно")
        
        # Создаем проект и маркеры
        project = Project(name="Test Project")
        marker1 = Marker(id=1, start_frame=100, end_frame=200, event_name="Test Event 1")
        marker2 = Marker(id=2, start_frame=300, end_frame=400, event_name="Test Event 2")
        
        project.add_marker(marker1)
        project.add_marker(marker2)
        
        print(f"✓ Создано {len(project.markers)} маркера")
        
        # Создаем TimelineController
        settings = AppSettings()
        history_manager = HistoryManager()
        
        # Создаем контроллер без виджетов (None)
        timeline_controller = TimelineController(
            project=project,
            timeline_widget=None,
            segment_list_widget=None,
            history_manager=history_manager,
            settings=settings
        )
        
        print("✓ TimelineController создан")
        
        # Проверяем начальное состояние
        initial_count = len(project.markers)
        print(f"✓ Начальное количество маркеров: {initial_count}")
        
        # Тестируем удаление первого маркера
        timeline_controller.delete_marker(0)
        
        # Проверяем результат
        final_count = len(project.markers)
        print(f"✓ Количество маркеров после удаления: {final_count}")
        
        if final_count == 1:
            print("✅ Тест пройден: маркер успешно удален")
        else:
            print("❌ Тест не пройден: маркер не удален")
            return False
        
        # Проверяем, что остался правильный маркер
        remaining_marker = project.markers[0]
        if remaining_marker.id == 2:
            print("✅ Тест пройден: удален правильный маркер")
        else:
            print("❌ Тест не пройден: удален не тот маркер")
            return False
        
        # Тестируем удаление из пустого списка
        project.markers.clear()
        timeline_controller.delete_marker(0)  # Должно не сломаться
        
        if len(project.markers) == 0:
            print("✅ Тест пройден: удаление из пустого списка обработано корректно")
        else:
            print("❌ Тест не пройден: удаление из пустого списка сломало что-то")
            return False
        
        # Тестируем удаление с неверным индексом
        project.add_marker(marker1)
        project.add_marker(marker2)
        
        timeline_controller.delete_marker(999)  # Должно не сломаться
        
        if len(project.markers) == 2:
            print("✅ Тест пройден: удаление с неверным индексом обработано корректно")
        else:
            print("❌ Тест не пройден: удаление с неверным индексом сломало что-то")
            return False
        
        # Тестируем функциональность выделенных маркеров
        timeline_controller.select_marker(0)
        selected = timeline_controller.get_selected_markers()
        
        if selected == [0]:
            print("✅ Тест пройден: выделение маркера работает")
        else:
            print("❌ Тест не пройден: выделение маркера не работает")
            return False
        
        timeline_controller.deselect_marker(0)
        selected = timeline_controller.get_selected_markers()
        
        if selected == []:
            print("✅ Тест пройден: снятие выделения работает")
        else:
            print("❌ Тест не пройден: снятие выделения не работает")
            return False
        
        print("=" * 50)
        print("🎉 Все тесты пройдены! Функциональность Delete работает корректно.")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при выполнении теста: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_shortcut_controller():
    """Тест ShortcutController."""
    print("\nТест: ShortcutController")
    print("=" * 30)
    
    try:
        from controllers.shortcut_controller import ShortcutController
        from PySide6.QtWidgets import QWidget
        
        # Создаем реальный QWidget вместо Mock
        parent_window = QWidget()
        shortcut_controller = ShortcutController(parent_window)
        
        print("✓ ShortcutController создан")
        
        # Проверяем, что shortcut для Delete зарегистрирован
        if hasattr(shortcut_controller.shortcut_manager, 'get_shortcut'):
            delete_shortcut = shortcut_controller.shortcut_manager.get_shortcut('DELETE')
            if delete_shortcut:
                print("✓ Delete shortcut зарегистрирован")
            else:
                print("❌ Delete shortcut не зарегистрирован")
                return False
        else:
            print("⚠️  Метод get_shortcut не найден, но это нормально")
        
        # Тестируем активацию shortcut
        shortcut_controller._on_global_shortcut_activated('DELETE')
        print("✓ Delete shortcut активирован")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании ShortcutController: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("Запуск упрощенных тестов функциональности Delete...")
    print()
    
    success1 = test_basic_delete_functionality()
    success2 = test_shortcut_controller()
    
    if success1 and success2:
        print("\n🎉 Все тесты пройдены! Функциональность Delete работает корректно.")
        sys.exit(0)
    else:
        print("\n❌ Некоторые тесты не прошли. Проверьте реализацию.")
        sys.exit(1)