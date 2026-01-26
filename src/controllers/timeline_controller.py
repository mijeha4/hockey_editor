from typing import List, Dict, Optional
from PySide6.QtCore import Signal, QObject

# Используем абсолютные импорты для работы из корня проекта
from models.domain.marker import Marker
from models.domain.project import Project
from models.config.app_settings import AppSettings
from services.history import HistoryManager
from views.widgets.segment_list import SegmentListWidget
from views.widgets.timeline_scene import TimelineWidget  # New timeline widget
from services.history.command_interface import Command


class AddMarkerCommand(Command):
    """Команда добавления маркера."""

    def __init__(self, project: Project, marker: Marker):
        super().__init__(f"Add {marker.event_name} marker")
        self.project = project
        self.marker = marker
        self.index = -1  # Индекс, куда был добавлен маркер

    def execute(self):
        """Добавить маркер."""
        self.index = len(self.project.markers)
        self.project.add_marker(self.marker, self.index)

    def undo(self):
        """Удалить маркер."""
        if self.index >= 0:
            self.project.remove_marker(self.index)


class TimelineController(QObject):
    """Контроллер управления маркерами с синхронизацией UI."""

    # Сигналы для новой TimelineWidget
    markers_changed = Signal()
    playback_time_changed = Signal(int)
    timeline_update = Signal()
    marker_updated = Signal(int)  # Индекс измененного маркера

    # Сигнал для уведомления об изменениях проекта
    project_modified = Signal()

    # Сигнал для уведомления о состоянии записи (dynamic mode)
    recording_state_changed = Signal(bool, str, int)  # is_recording, event_name, start_frame

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

        # Подключить сигналы проекта для реактивности
        self.project.marker_added.connect(self.on_marker_added)
        self.project.marker_removed.connect(self.on_marker_removed)
        self.project.marker_changed.connect(self.on_marker_changed)
        self.project.markers_cleared.connect(self.on_markers_cleared)

        # Подключить сигналы от View (если timeline_widget уже создан)
        if self.timeline_widget is not None:
            self._connect_timeline_signals()

        # Подключить сигнал markers_changed к обновлению timeline
        self.markers_changed.connect(self._on_markers_changed_internal)

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

    def on_marker_added(self, index: int, marker: Marker):
        """Обработчик добавления маркера."""
        # Обновить timeline с анимацией для нового маркера
        if self.timeline_widget:
            self.timeline_widget.rebuild(animate_new=True)

        # Обновить таблицу сегментов
        if self.segment_list_widget:
            self.segment_list_widget.update_segments([marker.to_marker() for marker in self.project.markers])

    def on_marker_removed(self, index: int):
        """Обработчик удаления маркера."""
        # Отправить сигнал об изменении маркеров для timeline и segment_list
        self.markers_changed.emit()

    def on_marker_changed(self, index: int, marker: Marker):
        """Обработчик изменения маркера."""
        # Отправить сигнал об изменении маркеров для timeline и segment_list
        self.markers_changed.emit()

    def on_markers_cleared(self):
        """Обработчик очистки всех маркеров."""
        # Отправить сигнал об изменении маркеров для timeline и segment_list
        self.markers_changed.emit()

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
            # Уведомить о начале записи
            self.recording_state_changed.emit(True, event_name, current_frame)
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
            # Уведомить о завершении записи
            self.recording_state_changed.emit(False, "", 0)

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

        # Уведомить об изменении проекта
        self.project_modified.emit()

    def modify_marker(self, marker_idx: int, new_marker):
        """Изменить существующий маркер."""
        if 0 <= marker_idx < len(self.project.markers):
            old_marker = self.project.markers[marker_idx]

            # Создать команду модификации
            command = ModifyMarkerCommand(self.project.markers, marker_idx, old_marker, new_marker)
            self.history_manager.execute_command(command)

            # Уведомить об изменении проекта
            self.project_modified.emit()

    def _on_timeline_seek(self, frame: int):
        """Обработка клика по таймлайну для перемотки."""
        print(f"Timeline seek to frame: {frame}")
        self.seek_frame(frame)

    def _on_event_selected(self, marker: Marker):
        """Обработка выбора события в timeline."""
        # Find marker index and highlight in segment list
        try:
            marker_idx = self.project.markers.index(marker)
            if self.segment_list_widget and hasattr(self.segment_list_widget, 'table'):
                # Find row in table by marker_idx
                for row in range(self.segment_list_widget.table.rowCount()):
                    item = self.segment_list_widget.table.item(row, 0)
                    if item and item.data(Qt.ItemDataRole.UserRole) == marker_idx:
                        self.segment_list_widget.table.selectRow(row)
                        break
        except ValueError:
            pass  # Marker not found

    def _on_event_double_clicked(self, marker: Marker):
        """Обработка двойного клика по событию для редактирования."""
        # Find marker index
        try:
            marker_idx = self.project.markers.index(marker)
            self.edit_marker_requested(marker_idx)
        except ValueError:
            pass  # Marker not found

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

        # Update timeline current time line
        if self.timeline_widget:
            self.timeline_widget.set_current_frame(self.current_frame, self.fps)

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

        # Обновить таймлайн - полная перерисовка для совместимости (без анимации)
        if self.timeline_widget:
            self.timeline_widget.rebuild(animate_new=False)

        # Обновить таблицу сегментов - полная перерисовка для совместимости
        if self.segment_list_widget:
            self.segment_list_widget.update_segments([marker.to_marker() for marker in self.project.markers])

    def set_timeline_widget(self, timeline_widget):
        """Установить timeline widget и подключить сигналы."""
        self.timeline_widget = timeline_widget
        if self.timeline_widget is not None:
            self._connect_timeline_signals()

    def _connect_timeline_signals(self):
        """Подключить сигналы timeline widget."""
        if self.timeline_widget is None:
            return

        # Проверяем, какой тип timeline widget используется
        # Новый TimelineWidget из hockey_editor.ui.timeline_graphics имеет scene.seek_requested
        if hasattr(self.timeline_widget, 'scene') and hasattr(self.timeline_widget.scene, 'seek_requested'):
            self.timeline_widget.scene.seek_requested.connect(self._on_timeline_seek)
            if hasattr(self.timeline_widget.scene, 'event_double_clicked'):
                self.timeline_widget.scene.event_double_clicked.connect(self._on_event_double_clicked)
            if hasattr(self.timeline_widget.scene, 'event_selected'):
                self.timeline_widget.scene.event_selected.connect(self._on_event_selected)
        # Старый TimelineWidget из src/views/widgets/timeline.py имеет seek_requested напрямую
        elif hasattr(self.timeline_widget, 'seek_requested'):
            self.timeline_widget.seek_requested.connect(self._on_timeline_seek)
            # Connect segment edit signal for double-click functionality
            if hasattr(self.timeline_widget, 'segment_edit_requested'):
                self.timeline_widget.segment_edit_requested.connect(self._on_event_double_clicked)

    def _on_markers_changed_internal(self):
        """Внутренний обработчик изменения маркеров для обновления UI."""
        if self.timeline_widget and hasattr(self.timeline_widget, 'set_markers'):
            # Update markers in new timeline widget
            self.timeline_widget.set_markers(self.project.markers)

        if self.segment_list_widget:
            # Обновить таблицу сегментов
            self.segment_list_widget.update_segments([marker.to_marker() for marker in self.project.markers])

    def edit_marker_requested(self, marker_idx: int):
        """Обработка запроса на редактирование маркера."""
        # Упрощаем проверку, так как теперь переменная точно существует (равна None или окну)
        if self._main_window:
            self._main_window.open_segment_editor(marker_idx)

    def init_tracks(self, total_frames: int):
        """Инициализировать таймлайн с общим количеством кадров."""
        self.set_total_frames(total_frames)
        if self.timeline_widget is not None:
            # Get track names from event manager
            track_names = self._get_track_names()
            self.timeline_widget.init_tracks(track_names, total_frames, self.fps)
            # Set initial markers
            self.timeline_widget.set_markers(self.project.markers)

    def _get_track_names(self) -> List[str]:
        """Get list of track names (event types) for timeline."""
        # Default hockey event types
        default_tracks = [
            "Заблокировано", "Блокшот в обороне", "Вброс", "Вбрасывание: Пропущено",
            "Вбрасывание: Проиграно", "Гол", "Бросок мимо", "Удаление",
            "Бросок в створ", "Перехват", "Потеря", "Вход в зону", "Выход из зоны"
        ]

        # Try to get from event manager
        try:
            from services.events.custom_event_manager import get_custom_event_manager
            event_manager = get_custom_event_manager()
            if event_manager:
                custom_events = event_manager.get_all_events()
                if custom_events:
                    # Use custom events + defaults for any missing
                    custom_names = [event.name for event in custom_events]
                    # Add defaults that aren't in custom
                    for default in default_tracks:
                        if default not in custom_names:
                            custom_names.append(default)
                    return custom_names
        except ImportError:
            pass

        return default_tracks

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
        indices_to_remove = []
        for i, marker in enumerate(self.project.markers):
            if marker.event_name == event_name:
                indices_to_remove.append(i)

        # Удалить найденные маркеры через команды (для поддержки undo/redo)
        for index in reversed(indices_to_remove):  # Удаляем с конца, чтобы индексы оставались корректными
            marker = self.project.markers[index]
            # Создать команду удаления для каждого маркера
            delete_command = DeleteMarkerCommand(self.project.markers, marker)
            self.history_manager.execute_command(delete_command)

        # Обновить UI если были удалены маркеры
        if indices_to_remove:
            print(f"TimelineController: Removed {len(indices_to_remove)} markers with deleted event '{event_name}'")
            # Уведомить об изменении проекта
            self.project_modified.emit()

    def update_marker_optimized(self, marker_idx: int, new_start: int, new_end: int, new_event_name: str = None, new_note: str = None):
        """Оптимизированное обновление конкретного маркера без полной перерисовки."""
        if 0 <= marker_idx < len(self.project.markers):
            marker = self.project.markers[marker_idx]
            
            # Сохранить старые значения для команды
            old_start = marker.start_frame
            old_end = marker.end_frame
            old_event_name = marker.event_name
            old_note = marker.note
            
            # Обновить маркер
            marker.start_frame = new_start
            marker.end_frame = new_end
            if new_event_name is not None:
                marker.event_name = new_event_name
            if new_note is not None:
                marker.note = new_note
            
            # Создать команду для истории
            old_marker = Marker(old_start, old_end, old_event_name, old_note)
            new_marker = Marker(new_start, new_end, new_event_name or old_event_name, new_note or old_note)
            command = ModifyMarkerCommand(self.project.markers, marker_idx, old_marker, new_marker)
            self.history_manager.execute_command(command)
            
            # Отправить сигнал об обновлении конкретного маркера
            self.marker_updated.emit(marker_idx)
            
            # Уведомить об изменении проекта
            self.project_modified.emit()
