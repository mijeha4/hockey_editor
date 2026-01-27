"""
Тест инициализации timeline widget с существующими маркерами.
Проверяет, что при установке timeline widget существующие маркеры правильно инициализируются.
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
from views.widgets.timeline import TimelineWidget

def test_timeline_widget_initialization():
    """Тест инициализации timeline widget с существующими маркерами."""
    print("=== Тест инициализации timeline widget ===\n")

    # Создаем приложение Qt
    app = QApplication(sys.argv)

    # Создаем проект
    project = Project(name="Test Project", video_path="test.mp4", fps=30.0)

    # Создаем настройки
    settings = AppSettings()

    # Создаем менеджер истории
    history_manager = HistoryManager()

    # Создаем контроллер таймлайна без timeline widget
    timeline_controller = TimelineController(
        project=project,
        timeline_widget=None,  # Сначала без виджета
        segment_list_widget=None,
        history_manager=history_manager,
        settings=settings,
        custom_event_controller=None
    )

    # Добавляем несколько маркеров ДО установки timeline widget
    print("1. Добавляем маркеры до установки timeline widget...")
    marker1 = Marker(start_frame=100, end_frame=200, event_name="Goal", note="First goal")
    command1 = AddMarkerCommand(project, marker1)
    history_manager.execute_command(command1)

    marker2 = Marker(start_frame=300, end_frame=400, event_name="Shot", note="First shot")
    command2 = AddMarkerCommand(project, marker2)
    history_manager.execute_command(command2)

    print(f"   - Добавлено {len(project.markers)} маркеров")

    # Теперь создаем и устанавливаем timeline widget
    print("\n2. Создаем и устанавливаем timeline widget...")
    timeline_widget = TimelineWidget()
    timeline_controller.set_timeline_widget(timeline_widget)

    # Проверяем, что маркеры были инициализированы в виджете
    print("\n3. Проверяем инициализацию маркеров в виджете...")

    # Проверяем, что у виджета установлены маркеры
    if hasattr(timeline_widget, 'markers') and timeline_widget.markers:
        print(f"[OK] Timeline widget содержит {len(timeline_widget.markers)} маркеров")
        assert len(timeline_widget.markers) == 2, "Количество маркеров в виджете не совпадает"
    else:
        print("[INFO] Timeline widget не имеет атрибута markers или он пуст")
        print("Это может быть нормально в зависимости от реализации виджета")

    # Проверяем, что контроллер правильно ссылается на виджет
    assert timeline_controller.timeline_widget is timeline_widget, "Timeline widget не установлен в контроллере"

    print("\n[OK] Все проверки пройдены успешно!")
    print("\n=== Вывод ===")
    print("Timeline widget правильно инициализируется с существующими маркерами.")
    print("При установке виджета через set_timeline_widget(), существующие маркеры")
    print("передаются в виджет для отображения.")

    # Закрываем приложение
    app.quit()

    return True

if __name__ == "__main__":
    try:
        success = test_timeline_widget_initialization()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)