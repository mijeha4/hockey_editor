from typing import List, Dict

# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.marker import Marker
    from models.domain.project import Project
    from services.history import HistoryManager, Command
    from views.components.timeline.scene import TimelineScene
except ImportError:
    # Для случаев, когда запускаем из src/
    from ..models.domain.marker import Marker
    from ..models.domain.project import Project
    from ..services.history import HistoryManager, Command
    from ..views.components.timeline.scene import TimelineScene


class AddMarkerCommand(Command):
    """Команда добавления маркера."""

    def __init__(self, project: Project, marker: Marker):
        super().__init__(f"Add {marker.event_name} marker")
        self.project = project
        self.marker = marker

    def execute(self):
        """Добавить маркер."""
        self.project.markers.append(self.marker)

    def undo(self):
        """Удалить маркер."""
        if self.marker in self.project.markers:
            self.project.markers.remove(self.marker)


class TimelineController:
    """Контроллер управления маркерами."""

    def __init__(self, project: Project,
                 timeline_scene: TimelineScene,
                 history_manager: HistoryManager):
        self.project = project
        self.timeline_scene = timeline_scene
        self.history_manager = history_manager

        # Подключить сигналы от View
        self.timeline_scene.marker_clicked.connect(self._on_marker_clicked)
        self.timeline_scene.marker_moved.connect(self._on_marker_moved)

    def add_marker(self, start_frame: int, end_frame: int, event_name: str, note: str = ""):
        """Добавить маркер."""
        marker = Marker(
            start_frame=start_frame,
            end_frame=end_frame,
            event_name=event_name,
            note=note
        )

        command = AddMarkerCommand(self.project, marker)
        self.history_manager.execute_command(command)

        # Обновить View
        self.refresh_view()

    def _on_marker_clicked(self, marker_id: int):
        """Обработка клика на маркере."""
        print(f"Marker clicked: {marker_id}")
        # Здесь можно открыть диалог редактирования

    def _on_marker_moved(self, marker_id: int, new_start: int, new_end: int):
        """Обработка перемещения маркера."""
        print(f"Marker moved: {marker_id} -> {new_start}-{new_end}")
        # Здесь можно создать команду изменения

    def refresh_view(self):
        """Обновить отображение маркеров."""
        markers_data = []
        for i, marker in enumerate(self.project.markers):
            markers_data.append({
                'id': i,
                'start_frame': marker.start_frame,
                'end_frame': marker.end_frame,
                'color': '#FF0000',  # Пока фиксированный цвет
                'event_name': marker.event_name,
                'note': marker.note
            })

        self.timeline_scene.set_markers(markers_data)
