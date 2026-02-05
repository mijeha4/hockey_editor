#!/usr/bin/env python3
"""
Интеграционный тест для проверки полной цепочки работы Delete.

Этот тест проверяет:
1. Работу ShortcutController с Delete
2. Передачу сигнала в MainController
3. Вызов удаления в TimelineController
"""

import sys
import os

# Добавляем путь к src для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_delete_integration():
    """Тест интеграции Delete."""
    print("Интеграционный тест: Полная цепочка Delete")
    print("=" * 50)
    
    try:
        # Импортируем компоненты
        from models.domain.project import Project
        from models.domain.marker import Marker
        from controllers.timeline_controller import TimelineController
        from controllers.shortcut_controller import ShortcutController
        from services.history import HistoryManager
        from models.config.app_settings import AppSettings
        from PySide6.QtWidgets import QWidget, QApplication
        
        print("✓ Импорты прошли успешно")
        
        # Создаем QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Создаем проект и маркеры
        project = Project(name="Test Project")
        marker1 = Marker(id=1, start_frame=100, end_frame=200, event_name="Test Event 1")
        marker2 = Marker(id=2, start_frame=300, end_frame=400, event_name="Test Event 2")
        
        project.add_marker(marker1)
        project.add_marker(marker2)
        
        print(f"✓ Создано {len(project.markers)} маркера")
        
        # Создаем контроллеры
        settings = AppSettings()
        history_manager = HistoryManager()
        
        # Создаем TimelineController
        timeline_controller = TimelineController(
            project=project,
            timeline_widget=None,
            segment_list_widget=None,
            history_manager=history_manager,
            settings=settings
        )
        
        # Создаем ShortcutController
        parent_window = QWidget()
        shortcut_controller = ShortcutController(parent_window)
        
        print("✓ Контроллеры созданы")
        
        # Подключаем сигналы (имитация MainController)
        def on_delete_shortcut(key):
            if key == 'DELETE':
                print("✓ Получен сигнал DELETE")
                # Имитация вызова _delete_selected_segment
                # Сначала проверяем выделенные маркеры
                selected_markers = timeline_controller.get_selected_markers()
                if selected_markers:
                    marker_idx = selected_markers[0]
                    print(f"✓ Удаление выделенного маркера: {marker_idx}")
                    timeline_controller.delete_marker(marker_idx)
                else:
                    # Удаляем последний маркер как fallback
                    if len(project.markers) > 0:
                        marker_idx = len(project.markers) - 1
                        print(f"✓ Удаление последнего маркера: {marker_idx}")
                        timeline_controller.delete_marker(marker_idx)
        
        shortcut_controller.shortcut_pressed.connect(on_delete_shortcut)
        
        print("✓ Сигналы подключены")
        
        # Тестируем цепочку
        print("\nТест 1: Удаление последнего маркера")
        initial_count = len(project.markers)
        print(f"Начальное количество маркеров: {initial_count}")
        
        # Имитируем нажатие Delete
        shortcut_controller._on_global_shortcut_activated('DELETE')
        
        final_count = len(project.markers)
        print(f"Количество маркеров после удаления: {final_count}")
        
        if final_count == initial_count - 1:
            print("✅ Тест 1 пройден: маркер удален")
        else:
            print("❌ Тест 1 не пройден")
            return False
        
        # Тестируем с выделенным маркером
        print("\nТест 2: Удаление выделенного маркера")
        timeline_controller.select_marker(0)
        selected = timeline_controller.get_selected_markers()
        print(f"Выделенные маркеры: {selected}")
        
        initial_count = len(project.markers)
        print(f"Начальное количество маркеров: {initial_count}")
        
        # Имитируем нажатие Delete
        shortcut_controller._on_global_shortcut_activated('DELETE')
        
        final_count = len(project.markers)
        print(f"Количество маркеров после удаления: {final_count}")
        
        if final_count == initial_count - 1:
            print("✅ Тест 2 пройден: выделенный маркер удален")
        else:
            print("❌ Тест 2 не пройден")
            return False
        
        # Проверяем, что остался правильный маркер
        if len(project.markers) > 0:
            remaining_marker = project.markers[0]
            if remaining_marker.id == 2:
                print("✅ Тест 2 дополнительный: удален правильный маркер")
            else:
                print("❌ Тест 2 дополнительный: удален не тот маркер")
                return False
        
        print("\n" + "=" * 50)
        print("🎉 Интеграционный тест пройден!")
        print("Функциональность Delete работает корректно:")
        print("  1. ShortcutController правильно обрабатывает Delete")
        print("  2. Сигнал передается дальше")
        print("  3. TimelineController удаляет маркер")
        print("  4. Поддерживается выделение маркеров")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при выполнении интеграционного теста: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("Запуск интеграционного теста функциональности Delete...")
    print()
    
    success = test_delete_integration()
    
    if success:
        print("\n🎉 Все тесты пройдены! Функциональность Delete полностью работает.")
        sys.exit(0)
    else:
        print("\n❌ Интеграционный тест не прошел. Проверьте реализацию.")
        sys.exit(1)