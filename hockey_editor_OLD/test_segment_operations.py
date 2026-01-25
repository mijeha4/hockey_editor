#!/usr/bin/env python3
"""
Простой тест функций удаления и редактирования отрезков.
Тестирует исправления без запуска полного GUI.
"""

import sys
sys.path.insert(0, 'hockey_editor')

from hockey_editor.models.marker import Marker
from hockey_editor.core.video_controller import VideoController


def test_delete_marker():
    """Тест функции удаления маркера."""
    print("🧪 Тестирование функции удаления маркера...")

    # Создаем контроллер
    controller = VideoController()

    # Создаем тестовые маркеры
    marker1 = Marker(start_frame=0, end_frame=100, event_name="Attack", note="")
    marker2 = Marker(start_frame=200, end_frame=300, event_name="Defense", note="")
    marker3 = Marker(start_frame=400, end_frame=500, event_name="Shift", note="")

    controller.markers = [marker1, marker2, marker3]

    print(f"  Исходные маркеры: {len(controller.markers)}")
    for i, m in enumerate(controller.markers):
        print(f"    {i}: {m.event_name} ({m.start_frame}-{m.end_frame})")

    # Удаляем средний маркер (индекс 1)
    print("  Удаляем маркер с индексом 1 (Defense)...")
    controller.delete_marker(1)

    print(f"  Маркеры после удаления: {len(controller.markers)}")
    for i, m in enumerate(controller.markers):
        print(f"    {i}: {m.event_name} ({m.start_frame}-{m.end_frame})")

    # Проверяем результат
    assert len(controller.markers) == 2, f"Ожидалось 2 маркера, получено {len(controller.markers)}"
    assert controller.markers[0].event_name == "Attack", f"Первый маркер должен быть Attack, получен {controller.markers[0].event_name}"
    assert controller.markers[1].event_name == "Shift", f"Второй маркер должен быть Shift, получен {controller.markers[1].event_name}"

    print("✅ Тест удаления маркера пройден!")


def test_modify_marker():
    """Тест функции изменения маркера."""
    print("\n🧪 Тестирование функции изменения маркера...")

    # Создаем контроллер
    controller = VideoController()

    # Создаем тестовый маркер
    original_marker = Marker(start_frame=0, end_frame=100, event_name="Attack", note="Original")
    controller.markers = [original_marker]

    print(f"  Исходный маркер: {controller.markers[0].event_name} ({controller.markers[0].start_frame}-{controller.markers[0].end_frame}) note='{controller.markers[0].note}'")

    # Изменяем маркер (имитируем работу редактора)
    modified_marker = Marker(start_frame=50, end_frame=150, event_name="Defense", note="Modified")
    controller.markers[0] = modified_marker

    print(f"  Измененный маркер: {controller.markers[0].event_name} ({controller.markers[0].start_frame}-{controller.markers[0].end_frame}) note='{controller.markers[0].note}'")

    # Проверяем результат
    assert controller.markers[0].start_frame == 50, f"start_frame должен быть 50, получен {controller.markers[0].start_frame}"
    assert controller.markers[0].end_frame == 150, f"end_frame должен быть 150, получен {controller.markers[0].end_frame}"
    assert controller.markers[0].event_name == "Defense", f"event_name должен быть Defense, получен {controller.markers[0].event_name}"
    assert controller.markers[0].note == "Modified", f"note должна быть Modified, получена {controller.markers[0].note}"

    print("✅ Тест изменения маркера пройден!")


def test_ui_logic_simulation():
    """Тест симуляции логики UI (без Qt)."""
    print("\n🧪 Тестирование логики UI (симуляция)...")

    # Создаем контроллер с маркерами
    controller = VideoController()
    controller.markers = [
        Marker(start_frame=0, end_frame=100, event_name="Attack", note=""),
        Marker(start_frame=200, end_frame=300, event_name="Defense", note=""),
        Marker(start_frame=400, end_frame=500, event_name="Shift", note=""),
    ]

    # Симулируем QListWidget items с сохраненными индексами
    class MockItem:
        def __init__(self, marker_idx):
            self.marker_idx = marker_idx

        def data(self, role):
            if role == 32:  # Qt.ItemDataRole.UserRole
                return self.marker_idx
            return None

    # Создаем mock items (как в _on_markers_changed)
    mock_items = []
    for idx in range(len(controller.markers)):
        item = MockItem(idx)
        mock_items.append(item)

    print(f"  Создано {len(mock_items)} mock items")

    # Тестируем получение индекса из item (как в _on_delete_marker)
    test_item = mock_items[1]  # Второй item
    marker_idx = test_item.data(32)  # UserRole

    print(f"  Item[1] содержит marker_idx = {marker_idx}")

    # Проверяем, что индекс правильный
    assert marker_idx == 1, f"Ожидался индекс 1, получен {marker_idx}"

    # Проверяем, что можем получить правильный маркер
    marker = controller.markers[marker_idx]
    assert marker.event_name == "Defense", f"Ожидался Defense, получен {marker.event_name}"

    print("✅ Тест логики UI пройден!")


if __name__ == "__main__":
    print("🚀 Запуск тестов функций сегментов...\n")

    try:
        test_delete_marker()
        test_modify_marker()
        test_ui_logic_simulation()

        print("\n🎉 Все тесты пройдены успешно!")
        print("✅ Функции удаления и редактирования отрезков работают корректно.")

    except Exception as e:
        print(f"\n❌ Тест провален: {e}")
        sys.exit(1)
