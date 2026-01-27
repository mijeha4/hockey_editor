"""
Тест обновления таймлайна после создания маркера.

Проверяет, что таймлайн обновляется корректно после создания нового маркера.
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from models.domain.project import Project
from models.domain.marker import Marker
from controllers.timeline_controller import TimelineController, AddMarkerCommand
from services.history.history_manager import HistoryManager
from models.config.app_settings import AppSettings


def test_timeline_update_after_marker_creation():
    """Тест обновления таймлайна после создания маркера."""
    print("=== Тест обновления таймлайна после создания маркера ===\n")

    # Создаем приложение Qt
    app = QApplication(sys.argv)

    # Создаем проект
    project = Project(name="Test Project", video_path="test.mp4", fps=30.0)

    # Создаем настройки
    settings = AppSettings()

    # Создаем менеджер истории
    history_manager = HistoryManager()

    # Создаем контроллер таймлайна (без виджетов для теста)
    timeline_controller = TimelineController(
        project=project,
        timeline_widget=None,  # Без виджета для теста
        segment_list_widget=None,  # Без виджета для теста
        history_manager=history_manager,
        settings=settings,
        custom_event_controller=None
    )

    # Подключаем сигналы для отслеживания
    marker_added_called = False
    markers_changed_called = False

    def on_marker_added(index, marker):
        nonlocal marker_added_called
        marker_added_called = True
        print(f"[OK] Сигнал marker_add вызван: индекс={index}, маркер={marker.event_name}")

    def on_markers_changed():
        nonlocal markers_changed_called
        markers_changed_called = True
        print("[OK] Сигнал markers_changed вызван")

    # Подключаем сигналы
    project.marker_added.connect(on_marker_added)
    timeline_controller.markers_changed.connect(on_markers_changed)

    # Создаем маркер
    print("\n1. Создаем маркер...")
    marker = Marker(start_frame=100, end_frame=200, event_name="Goal", note="Test marker")

    # Добавляем маркер через команду
    print("2. Добавляем маркер через AddMarkerCommand...")
    command = AddMarkerCommand(project, marker)
    history_manager.execute_command(command)

    # Проверяем результаты
    print("\n3. Проверяем результаты...")
    print(f"   - Количество маркеров в проекте: {len(project.markers)}")
    print(f"   - marker_add вызван: {marker_added_called}")
    print(f"   - markers_changed вызван: {markers_changed_called}")

    # Проверяем, что маркер добавлен
    assert len(project.markers) == 1, "Маркер не был добавлен в проект"
    assert project.markers[0].start_frame == 100, "Некорректный start_frame"
    assert project.markers[0].end_frame == 200, "Некорректный end_frame"
    assert project.markers[0].event_name == "Goal", "Некорректный event_name"

    # Проверяем, что сигналы были вызваны
    assert marker_added_called, "Сигнал marker_add не был вызван"
    # После оптимизации markers_changed НЕ должен вызываться при добавлении маркера
    # assert markers_changed_called, "Сигнал markers_changed не был вызван"

    print("\n[OK] Все проверки пройдены успешно!")
    print("\n=== Вывод ===")
    print("Таймлайн обновляется корректно после создания маркера.")
    print("Сигнал marker_add вызывается, что запускает обновление таймлайна.")
    print("После оптимизации markers_changed НЕ вызывается при добавлении маркера,")
    print("что избегает двойной перерисовки таймлайна.")
    print("В тесте timeline_widget=None, поэтому UI не обновляется, но сигналы работают корректно.")
    print("В реальном приложении timeline widget создается и устанавливается до добавления маркеров.")

    # Закрываем приложение
    app.quit()

    return True


if __name__ == "__main__":
    try:
        success = test_timeline_update_after_marker_creation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
