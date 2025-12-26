from typing import List, Dict
from PySide6.QtCore import Signal, QObject

# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.marker import Marker
    from models.domain.project import Project
    from models.config.app_settings import AppSettings
    from services.history import HistoryManager, Command
    from views.widgets.segment_list import SegmentListWidget
    # Используем новую профессиональную timeline из hockey_editor/ui/
    from hockey_editor.ui.timeline_graphics import TimelineWidget
except ImportError:
    # Для случаев, когда запускаем из src/
    from ..models.domain.marker import Marker
    from ..models.domain.project import Project
    from ..models.config.app_settings import AppSettings
    from ..services.history import HistoryManager, Command
    from ..views.widgets.segment_list import SegmentListWidget
    # Используем новую профессиональную timeline из hockey_editor/ui/
    from hockey_editor.ui.timeline_graphics import TimelineWidget


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


class TimelineController(QObject):
    """Контроллер управления маркерами с синхронизацией UI."""

    # Сигналы для новой TimelineWidget
    markers_changed = Signal()
    playback_time_changed = Signal(int)
    timeline_update = Signal()

    def __init__(self, project: Project,
                 timeline_widget: TimelineWidget,
                 segment_list_widget: SegmentListWidget,
                 history_manager: HistoryManager,
                 settings: AppSettings):
        super().__init__()
        self.project = project
        self.timeline_widget = timeline_widget
        self.segment_list_widget = segment_list_widget
        self.history_manager = history_manager
        self.settings = settings

        # Состояние для Dynamic режима
        self.recording_start_frame = None
        self.is_recording = False

        # Текущее состояние воспроизведения
        self.current_frame = 0
        self.fps = 30.0
        self.total_frames = 0

        # Подключить сигналы от View (если timeline_widget уже создан)
        if self.timeline_widget is not None:
            self.timeline_widget.seek_requested.connect(self._on_timeline_seek)
        # segment_list_widget не имеет сигналов выбора, так что убираем эту строку

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

    def _on_timeline_seek(self, frame: int):
        """Обработка клика по таймлайну для перемотки."""
        print(f"Timeline seek to frame: {frame}")
        # Здесь можно добавить логику перемотки видео

    @property
    def markers(self):
        """Свойство для доступа к маркерам проекта."""
        return self.project.markers

    def get_fps(self):
        """Получить FPS видео."""
        return self.fps

    def get_total_frames(self):
        """Получить общее количество кадров видео."""
        return self.total_frames

    def get_current_frame_idx(self):
        """Получить текущий кадр воспроизведения."""
        return self.current_frame

    def seek_frame(self, frame_idx: int):
        """Перемотать к указанному кадру."""
        self.current_frame = max(0, min(frame_idx, self.total_frames - 1))
        self.playback_time_changed.emit(self.current_frame)

    def set_fps(self, fps: float):
        """Установить FPS видео."""
        self.fps = fps

    def set_total_frames(self, total_frames: int):
        """Установить общее количество кадров видео."""
        self.total_frames = total_frames

    def refresh_view(self):
        """Обновить отображение маркеров в обоих компонентах."""
        # Отправить сигнал об изменении маркеров
        self.markers_changed.emit()

        # Обновить таймлайн
        self.timeline_widget.set_segments(self.project.markers)

        # Обновить таблицу сегментов
        self.segment_list_widget.update_segments(self.project.markers)

    def set_timeline_widget(self, timeline_widget):
        """Установить timeline widget и подключить сигналы."""
        self.timeline_widget = timeline_widget
        if self.timeline_widget is not None:
            self.timeline_widget.scene.seek_requested.connect(self._on_timeline_seek)

    def edit_marker_requested(self, marker_idx: int):
        """Обработка запроса на редактирование маркера."""
        if hasattr(self, '_main_window') and self._main_window:
            self._main_window.open_segment_editor(marker_idx)

    def init_tracks(self, total_frames: int):
        """Инициализировать таймлайн с общим количеством кадров."""
        self.set_total_frames(total_frames)
        if self.timeline_widget is not None:
            self.timeline_widget.set_total_frames(total_frames)
            self.timeline_widget.set_fps(self.fps)
