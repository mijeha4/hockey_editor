#!/usr/bin/env python3
"""
Тест обновления timeline после изменения маркеров.
Проверяет, что сигнал markers_changed испускается после modify_marker().
"""

import sys
sys.path.insert(0, 'hockey_editor')
sys.path.insert(0, 'src')

from PySide6.QtCore import QObject, Signal

# Используем те же импорты, что и в timeline_controller.py
try:
    from models.domain.marker import Marker
    from models.domain.project import Project
    from models.config.app_settings import AppSettings
    from services.history import HistoryManager
    from views.widgets.segment_list import SegmentListWidget
    from hockey_editor.ui.timeline_graphics import TimelineWidget
    from utils.commands.modify_marker_command import ModifyMarkerCommand
except ImportError:
    # Для случаев, когда запускаем из src/
    try:
        from ..models.domain.marker import Marker
        from ..models.domain.project import Project
        from ..models.config.app_settings import AppSettings
        from ..services.history import HistoryManager
        from ..views.widgets.segment_list import SegmentListWidget
        from hockey_editor.ui.timeline_graphics import TimelineWidget
        from ..utils.commands.modify_marker_command import ModifyMarkerCommand
    except ImportError:
        # Fallback для тестирования
        from models.domain.marker import Marker
        from models.domain.project import Project
        from models.config.app_settings import AppSettings
        from services.history import HistoryManager
        from views.widgets.segment_list import SegmentListWidget
        from hockey_editor.ui.timeline_graphics import TimelineWidget
        from hockey_editor.utils.commands.modify_marker_command import ModifyMarkerCommand

from controllers.timeline_controller import TimelineController


class MockTimelineWidget(QObject):
    """Mock timeline widget для тестирования сигналов."""

    seek_requested = Signal(int)  # Добавляем сигнал как в настоящем TimelineWidget

    def __init__(self):
        super().__init__()
        self.segments_updated = False
        self.markers_changed_received = False

    def set_segments(self, segments):
        """Mock метод set_segments."""
        self.segments_updated = True
        print(f"  TimelineWidget.set_segments() вызван с {len(segments)} сегментами")


class MockSegmentListWidget:
    """Mock segment list widget."""

    def __init__(self):
        self.segments_updated = False

    def update_segments(self, segments):
        """Mock метод update_segments."""
        self.segments_updated = True
        print(f"  SegmentListWidget.update_segments() вызван с {len(segments)} сегментами")


def test_timeline_update_after_marker_modify():
    """Тест обновления timeline после изменения маркера."""
    print("🧪 Тестирование обновления timeline после изменения маркера...")

    # Создаем проект с маркером
    project = Project(name="Test Project")
    original_marker = Marker(start_frame=0, end_frame=100, event_name="Attack", note="Original")
    project.markers = [original_marker]

    # Создаем mock widgets
    timeline_widget = MockTimelineWidget()
    segment_list_widget = MockSegmentListWidget()

    # Создаем контроллер
    settings = AppSettings()
    history_manager = HistoryManager()
    controller = TimelineController(
        project=project,
        timeline_widget=timeline_widget,
        segment_list_widget=segment_list_widget,
        history_manager=history_manager,
        settings=settings
    )

    # Подключаем сигнал markers_changed к mock
    def on_markers_changed():
        timeline_widget.markers_changed_received = True
        print("  Сигнал markers_changed получен")

    controller.markers_changed.connect(on_markers_changed)

    print(f"  Исходный маркер: {project.markers[0].event_name} ({project.markers[0].start_frame}-{project.markers[0].end_frame})")

    # Создаем измененный маркер
    modified_marker = Marker(start_frame=50, end_frame=150, event_name="Defense", note="Modified")

    # Вызываем modify_marker (как делает main_window._on_instance_updated)
    controller.modify_marker(0, modified_marker)

    print(f"  Измененный маркер: {project.markers[0].event_name} ({project.markers[0].start_frame}-{project.markers[0].end_frame})")

    # Проверяем, что маркер действительно изменился
    assert project.markers[0].start_frame == 50, f"start_frame должен быть 50, получен {project.markers[0].start_frame}"
    assert project.markers[0].end_frame == 150, f"end_frame должен быть 150, получен {project.markers[0].end_frame}"
    assert project.markers[0].event_name == "Defense", f"event_name должен быть Defense, получен {project.markers[0].event_name}"

    # Проверяем, что сигнал был отправлен
    assert timeline_widget.markers_changed_received, "Сигнал markers_changed не был получен"

    # Проверяем, что widgets были обновлены
    assert timeline_widget.segments_updated, "TimelineWidget не был обновлен"
    assert segment_list_widget.segments_updated, "SegmentListWidget не был обновлен"

    print("✅ Тест обновления timeline пройден!")


if __name__ == "__main__":
    print("🚀 Запуск теста обновления timeline...\n")

    try:
        test_timeline_update_after_marker_modify()
        print("\n🎉 Тест пройден успешно!")
        print("✅ Timeline обновляется корректно после изменения маркеров.")

    except Exception as e:
        print(f"\n❌ Тест провален: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
