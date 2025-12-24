from typing import List, Dict

# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.marker import Marker
    from models.domain.project import Project
    from models.config.app_settings import AppSettings
    from services.history import HistoryManager, Command
    from views.components.timeline.scene import TimelineScene
    from views.components.segment_list import SegmentList
except ImportError:
    # Для случаев, когда запускаем из src/
    from ..models.domain.marker import Marker
    from ..models.domain.project import Project
    from ..models.config.app_settings import AppSettings
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
                 history_manager: HistoryManager,
                 settings: AppSettings):
        self.project = project
        self.timeline_scene = timeline_scene
        self.segment_list = segment_list
        self.history_manager = history_manager
        self.settings = settings

        # Состояние для Dynamic режима
        self.recording_start_frame = None
        self.is_recording = False

        # Подключить сигналы от View
        self.timeline_scene.marker_clicked.connect(self._on_marker_clicked)
        self.segment_list.selection_changed.connect(self._on_segment_selected)

    def handle_hotkey(self, hotkey: str, current_frame: int, fps: float) -> None:
        """
        Обработка нажатия горячей клавиши.

        Args:
            hotkey: Нажатая клавиша (например, 'G', 'H', etc.)
            current_frame: Текущий кадр видео
            fps: FPS видео для конвертации времени
        """
        # Найти событие по горячей клавише
        event_type = self._find_event_by_hotkey(hotkey)
        if not event_type:
            return

        if self.settings.recording_mode == "dynamic":
            self._handle_dynamic_mode(event_type, current_frame, fps)
        elif self.settings.recording_mode == "fixed_length":
            self._handle_fixed_length_mode(event_type, current_frame, fps)

    def _find_event_by_hotkey(self, hotkey: str) -> str:
        """Найти тип события по горячей клавише."""
        for event in self.settings.default_events:
            if event.shortcut.upper() == hotkey.upper():
                return event.name
        return None

    def _handle_dynamic_mode(self, event_name: str, current_frame: int, fps: float) -> None:
        """
        Обработка Dynamic режима: два нажатия = начало и конец.
        """
        if not self.is_recording:
            # Первое нажатие - начало записи
            self.recording_start_frame = current_frame
            self.is_recording = True
            print(f"Started recording {event_name} at frame {current_frame}")
        else:
            # Второе нажатие - конец записи
            if self.recording_start_frame is not None:
                start_frame = self.recording_start_frame
                end_frame = current_frame

                # Применить pre-roll и post-roll
                start_frame = max(0, start_frame - int(self.settings.pre_roll_sec * fps))
                end_frame = end_frame + int(self.settings.post_roll_sec * fps)

                # Создать маркер
                self.add_marker(start_frame, end_frame, event_name)

                print(f"Completed recording {event_name}: {start_frame}-{end_frame}")

            # Сбросить состояние
            self.recording_start_frame = None
            self.is_recording = False

    def _handle_fixed_length_mode(self, event_name: str, current_frame: int, fps: float) -> None:
        """
        Обработка Fixed Length режима: одно нажатие = отрезок фиксированной длины.
        """
        # Формула: start = current - pre_roll, end = start + fixed_duration + post_roll
        start_frame = current_frame - int(self.settings.pre_roll_sec * fps)
        end_frame = start_frame + int(self.settings.fixed_duration_sec * fps) + int(self.settings.post_roll_sec * fps)

        # Ограничить границы
        start_frame = max(0, start_frame)

        # Создать маркер
        self.add_marker(start_frame, end_frame, event_name)
        print(f"Created fixed-length {event_name}: {start_frame}-{end_frame}")

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
        """Обновить отображение маркеров в обоих компонентах с правильными цветами и дорожками."""
        # Создаем маппинги из настроек
        color_map = {event.name: event.color for event in self.settings.default_events}
        row_map = {event.name: i for i, event in enumerate(self.settings.default_events)}

        # Данные для сцены таймлайна
        scene_markers_data = []
        # Данные для таблицы сегментов
        table_segments_data = []

        for i, marker in enumerate(self.project.markers):
            # Получаем цвет и индекс дорожки
            color = color_map.get(marker.event_name, '#CCCCCC')  # Серый по умолчанию
            track_index = row_map.get(marker.event_name, 0)      # Первая дорожка по умолчанию

            # Данные для сцены
            scene_markers_data.append({
                'id': i,
                'start_frame': marker.start_frame,
                'end_frame': marker.end_frame,
                'color': color,
                'event_name': marker.event_name,
                'note': marker.note,
                'track_index': track_index  # Добавляем индекс дорожки
            })

            # Данные для таблицы
            table_segments_data.append({
                'id': i,
                'event_name': marker.event_name,
                'start_frame': marker.start_frame,
                'end_frame': marker.end_frame,
                'color': color  # Правильный цвет для таблицы
            })

        # Обновить сцену таймлайна
        self.timeline_scene.set_markers(scene_markers_data)

        # Обновить таблицу сегментов
        self.segment_list.set_segments(table_segments_data)

    def init_tracks(self, total_frames: int):
        """Инициализировать дорожки с фоном и заголовками."""
        self.timeline_scene.init_tracks(self.settings.default_events, total_frames)
