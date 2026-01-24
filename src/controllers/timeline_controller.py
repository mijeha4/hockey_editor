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
    from utils.commands.modify_marker_command import ModifyMarkerCommand
    from utils.commands.delete_marker_command import DeleteMarkerCommand
except ImportError:
    # Для случаев, когда запускаем из src/
    try:
        from ..models.domain.marker import Marker
        from ..models.domain.project import Project
        from ..models.config.app_settings import AppSettings
        from ..services.history import HistoryManager, Command
        from ..views.widgets.segment_list import SegmentListWidget
        # Используем новую профессиональную timeline из hockey_editor/ui/
        from hockey_editor.ui.timeline_graphics import TimelineWidget
        from hockey_editor.utils.commands.modify_marker_command import ModifyMarkerCommand
        from hockey_editor.utils.commands.delete_marker_command import DeleteMarkerCommand
    except ImportError:
        # Fallback для тестирования
        from models.domain.marker import Marker
        from models.domain.project import Project
        from models.config.app_settings import AppSettings
        from services.history import HistoryManager, Command
        from views.widgets.segment_list import SegmentListWidget
        from hockey_editor.ui.timeline_graphics import TimelineWidget
        from hockey_editor.utils.commands.modify_marker_command import ModifyMarkerCommand


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

    # Сигнал для уведомления об изменениях проекта
    project_modified = Signal()

    def __init__(self, project: Project,
                 timeline_widget: TimelineWidget,
                 segment_list_widget: SegmentListWidget,
                 history_manager: HistoryManager,
                 settings: AppSettings,
                 custom_event_controller=None):
        super().__init__()
        self.project = project
        self.timeline_widget = timeline_widget
        self.segment_list_widget = segment_list_widget
        self.history_manager = history_manager
        self.settings = settings
        self.custom_event_controller = custom_event_controller

        # --- ДОБАВИТЬ ЭТУ СТРОКУ ---
        self._main_window = None
        # ---------------------------

        # Состояние для Dynamic режима
        self.recording_start_frame = None
        self.is_recording = False

        # Текущее состояние воспроизведения
        self.current_frame = 0
        self.fps = 30.0
        self.total_frames = 0

        # Ссылка на playback controller для синхронизации
        self.playback_controller = None

        # Подключить сигналы от View (если timeline_widget уже создан)
        if self.timeline_widget is not None:
            self.timeline_widget.seek_requested.connect(self._on_timeline_seek)
        # segment_list_widget не имеет сигналов выбора, так что убираем эту строку

        # Подключить сигналы от CustomEventController для синхронизации событий
        if self.custom_event_controller is not None:
            self.custom_event_controller.events_changed.connect(self._on_events_changed)
            self.custom_event_controller.event_added.connect(self._on_event_added)
            self.custom_event_controller.event_deleted.connect(self._on_event_deleted)

    # --- ДОБАВИТЬ ЭТОТ МЕТОД ---
    def set_main_window(self, window):
        """Установить ссылку на главное окно."""
        self._main_window = window
    # ---------------------------

    def set_playback_controller(self, playback_controller):
        """Установить ссылку на playback controller для синхронизации."""
        self.playback_controller = playback_controller

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
        # Сначала проверить кастомные события через контроллер
        if self.custom_event_controller:
            all_events = self.custom_event_controller.get_all_events()
            for event in all_events:
                if event.shortcut.upper() == hotkey.upper():
                    return event.name

        # Затем проверить дефолтные события
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

        # Уведомить об изменении проекта
        self.project_modified.emit()

    def modify_marker(self, marker_idx: int, new_marker):
        """Изменить существующий маркер."""
        if 0 <= marker_idx < len(self.project.markers):
            old_marker = self.project.markers[marker_idx]

            # Создать команду модификации
            command = ModifyMarkerCommand(self.project.markers, marker_idx, old_marker, new_marker)
            self.history_manager.execute_command(command)

            # Обновить View
            self.refresh_view()

            # Уведомить об изменении проекта
            self.project_modified.emit()

    def _on_timeline_seek(self, frame: int):
        """Обработка клика по таймлайну для перемотки."""
        print(f"Timeline seek to frame: {frame}")
        self.seek_frame(frame)

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

    def seek_frame(self, frame_idx: int, update_playback: bool = True):
        """Перемотать к указанному кадру.

        Args:
            frame_idx: Кадр для перемотки
            update_playback: Флаг, нужно ли обновлять playback controller
        """
        self.current_frame = max(0, min(frame_idx, self.total_frames - 1))

        # Синхронизировать с playback controller только если флаг установлен
        if update_playback and self.playback_controller:
            self.playback_controller.seek_to_frame(self.current_frame)

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
        # Упрощаем проверку, так как теперь переменная точно существует (равна None или окну)
        if self._main_window:
            self._main_window.open_segment_editor(marker_idx)

    def init_tracks(self, total_frames: int):
        """Инициализировать таймлайн с общим количеством кадров."""
        self.set_total_frames(total_frames)
        if self.timeline_widget is not None:
            self.timeline_widget.set_total_frames(total_frames)
            self.timeline_widget.set_fps(self.fps)

    def _on_events_changed(self):
        """Обработка изменения списка событий."""
        print("TimelineController: Events list changed, updating hotkey mappings")
        # Список событий изменился, но нам не нужно предпринимать специальных действий
        # TimelineController будет использовать актуальный список при следующем вызове _find_event_by_hotkey

    def _on_event_added(self, event):
        """Обработка добавления нового события."""
        print(f"TimelineController: New event added: {event.name} (shortcut: {event.shortcut})")
        # Новое событие добавлено, оно будет доступно при следующем поиске по горячим клавишам

    def _on_event_deleted(self, event_name: str):
        """Обработка удаления события."""
        print(f"TimelineController: Event deleted: {event_name}")

        # Удалить все маркеры с этим событием
        markers_to_remove = []
        for marker in self.project.markers:
            if marker.event_name == event_name:
                markers_to_remove.append(marker)

        # Удалить найденные маркеры через команды (для поддержки undo/redo)
        for marker in markers_to_remove:
            # Создать команду удаления для каждого маркера
            delete_command = DeleteMarkerCommand(self.project.markers, marker)
            self.history_manager.execute_command(delete_command)

        # Обновить UI если были удалены маркеры
        if markers_to_remove:
            print(f"TimelineController: Removed {len(markers_to_remove)} markers with deleted event '{event_name}'")
            self.refresh_view()
            # Уведомить об изменении проекта
            self.project_modified.emit()
