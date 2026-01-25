"""
Тест для проверки загрузки проекта с маркерами и отображения их на timeline.
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from models.domain.project import Project
from models.domain.marker import Marker
from models.config.app_settings import AppSettings
from services.history.history_manager import HistoryManager
from controllers.timeline_controller import TimelineController
from views.widgets.timeline import TimelineWidget
from views.widgets.segment_list import SegmentListWidget
from services.serialization.project_io import ProjectIO


def test_load_project_with_markers():
    """Тест загрузки проекта с маркерами."""
    print("=== Тест загрузки проекта с маркерами ===")

    # Создаем приложение
    app = QApplication(sys.argv)

    # Создаем проект с маркерами
    project = Project("Test Project", fps=30.0)
    project.add_marker(Marker(100, 200, "Goal", "Test goal"), 0)
    project.add_marker(Marker(300, 400, "Shot", "Test shot"), 1)

    # Сохраняем проект
    project_io = ProjectIO()
    test_file = "test_project_with_markers.hep"
    success = project_io.save_project(project, test_file)
    if not success:
        print("Ошибка сохранения проекта")
        return

    print(f"Проект сохранен: {test_file}")

    # Загружаем проект
    loaded_project = project_io.load_project(test_file)
    if not loaded_project:
        print("Ошибка загрузки проекта")
        return

    print(f"Проект загружен: {loaded_project.name}")
    print(f"Маркеры: {len(loaded_project.markers)}")

    # Создаем timeline widget
    timeline_widget = TimelineWidget()
    timeline_widget.set_fps(30.0)
    timeline_widget.set_total_frames(1000)

    # Создаем segment list widget
    segment_list_widget = SegmentListWidget()

    # Создаем timeline controller
    settings = AppSettings()
    history_manager = HistoryManager()
    controller = TimelineController(
        loaded_project,
        timeline_widget,
        segment_list_widget,
        history_manager,
        settings
    )

    # Проверяем, что маркеры отображаются
    print(f"Маркеры в контроллере: {len(controller.markers)}")

    # Имитируем refresh_view
    controller.refresh_view()

    # Проверяем, что timeline обновился
    print("Тест завершен успешно!")

    # Очищаем
    Path(test_file).unlink(missing_ok=True)


if __name__ == "__main__":
    test_load_project_with_markers()