from typing import List, Dict

# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.marker import Marker
    from models.domain.project import Project
    from services.history import HistoryManager, Command
    from views.components.timeline.scene import TimelineScene
    from views.components.segment_list import SegmentList
except ImportError:
    # Для случаев, когда запускаем из src/
    from ..models.domain.marker import Marker
    from ..models.domain.project import Project
    from ..services.history import HistoryManager, Command
    from ..views.components.timeline.scene import TimelineScene
    from ..views.components.segment_list import SegmentList


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
    """Контроллер управления маркерами с синхронизацией UI."""

    def __init__(self, project: Project,
                 timeline_scene: TimelineScene,
                 segment_list: SegmentList,
                 history_manager: HistoryManager):
        self.project = project
        self.timeline_scene = timeline_scene
        self.segment_list = segment_list
        self.history_manager = history_manager

        # Подключить сигналы от View
        self.timeline_scene.marker_clicked.connect(self._on_marker_clicked)
        self.segment_list.selection_changed.connect(self._on_segment_selected)

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
        """Обработка клика на маркере в сцене."""
        print(f"Marker clicked: {marker_id}")
        # Синхронизировать выделение в таблице
        self.segment_list.table.selectRow(marker_id)

    def _on_segment_selected(self, segment_id: int):
        """Обработка выбора сегмента в таблице."""
        print(f"Segment selected: {segment_id}")
        # Синхронизировать выделение в сцене
        # Здесь можно добавить логику выделения маркера на сцене

    def refresh_view(self):
        """Обновить отображение маркеров в обоих компонентах."""
        # Данные для сцены таймлайна
        scene_markers_data = []
        # Данные для таблицы сегментов
        table_segments_data = []

        for i, marker in enumerate(self.project.markers):
            # Данные для сцены
            scene_markers_data.append({
                'id': i,
                'start_frame': marker.start_frame,
                'end_frame': marker.end_frame,
                'color': '#FF0000',  # Пока фиксированный цвет
                'event_name': marker.event_name,
                'note': marker.note
            })

            # Данные для таблицы
            table_segments_data.append({
                'id': i,
                'event_name': marker.event_name,
                'start_frame': marker.start_frame,
                'end_frame': marker.end_frame,
                'color': '#FF0000'  # Пока фиксированный цвет
            })

        # Обновить сцену таймлайна
        self.timeline_scene.set_markers(scene_markers_data)

        # Обновить таблицу сегментов
        self.segment_list.set_segments(table_segments_data)
