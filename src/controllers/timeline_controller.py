from typing import List, Dict, Optional
from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QGraphicsRectItem

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


class ModifyMarkerCommand(Command):
    """Команда изменения маркера."""

    def __init__(self, markers_list, marker_idx: int, old_marker: Marker, new_marker: Marker):
        super().__init__(f"Modify {new_marker.event_name} marker")
        self.markers_list = markers_list
        self.marker_idx = marker_idx
        self.old_marker = old_marker
        self.new_marker = new_marker

    def execute(self):
        """Изменить маркер."""
        if 0 <= self.marker_idx < len(self.markers_list):
            self.markers_list[self.marker_idx] = self.new_marker

    def undo(self):
        """Вернуть старый маркер."""
        if 0 <= self.marker_idx < len(self.markers_list):
            self.markers_list[self.marker_idx] = self.old_marker


class DeleteMarkerCommand(Command):
    """Команда удаления маркера."""

    def __init__(self, project: Project, marker: Marker):
        super().__init__(f"Delete {marker.event_name} marker")
        self.project = project
        self.marker = marker
        self.index = -1  # Индекс, откуда был удален маркер

    def execute(self):
        """Удалить маркер."""
        try:
            self.index = self.project.markers.index(self.marker)
            self.project.remove_marker(self.index)
        except ValueError:
            self.index = -1

    def undo(self):
        """Вернуть маркер."""
        if self.index >= 0:
            self.project.add_marker(self.marker, self.index)


class TimelineController(QObject):
    """Контроллер управления маркерами с синхронизацией UI."""

    # Сигналы для новой TimelineWidget
    markers_changed = Signal()
    playback_time_changed = Signal(int)
    timeline_update = Signal()
    marker_updated = Signal(int)  # Индекс измененного маркера
    marker_selection_changed = Signal()  # Сигнал изменения выделения маркеров

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

        # Выделенные маркеры для операций удаления
        self.selected_markers = set()

        # Подключить сигналы проекта для реактивности
        self.project.marker_added.connect(self.on_marker_added)
        self.project.marker_removed.connect(self.on_marker_removed)
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

        # Подключить FilterController для синхронизации фильтров
        self.filter_controller = None
        if hasattr(self, 'project') and hasattr(self.project, 'filter_controller'):
            self.filter_controller = self.project.filter_controller
        elif hasattr(self, 'project') and hasattr(self.project, 'main_controller'):
            self.filter_controller = self.project.main_controller.filter_controller

        if self.filter_controller is not None:
            self.filter_controller.filters_changed.connect(self._on_filters_changed)
    # --- ДОБАВИТЬ ЭТОТ МЕТОД ---
    def set_main_window(self, window):
        """Установить ссылку на главное окно."""
        self._main_window = window
    # ---------------------------

    def set_playback_controller(self, playback_controller):
        """Установить ссылку на playback controller для синхронизации."""
        self.playback_controller = playback_controller

    def set_custom_event_controller(self, custom_event_controller):
        """Установить ссылку на custom_event_controller."""
        self.custom_event_controller = custom_event_controller
        if self.custom_event_controller is not None:
            self.custom_event_controller.events_changed.connect(self._on_events_changed)
            self.custom_event_controller.event_added.connect(self._on_event_added)
            self.custom_event_controller.event_deleted.connect(self._on_event_deleted)

    def set_filter_controller(self, filter_controller):
        """Установить ссылку на filter_controller."""
        self.filter_controller = filter_controller
        if self.filter_controller is not None:
            self.filter_controller.filters_changed.connect(self._on_filters_changed)

    def on_marker_added(self, index: int, marker: Marker):
        """Обработчик добавления маркера."""
        print(f"DEBUG: TimelineController.on_marker_added() called with index={index}, marker={marker.event_name}")
        print(f"DEBUG: timeline_widget is {self.timeline_widget}")
        print(f"DEBUG: segment_list_widget is {self.segment_list_widget}")

        # Обновить timeline с анимацией для нового маркера
        if self.timeline_widget:
            print("DEBUG: Calling timeline_widget.rebuild(animate_new=True)")
            try:
                # Ensure the timeline widget has the controller properly set
                if hasattr(self.timeline_widget, 'set_controller'):
                    if self.timeline_widget.controller is None:
                        self.timeline_widget.set_controller(self)
                        print("DEBUG: Set controller on timeline widget")
                    elif self.timeline_widget.controller != self:
                        # Reconnect with current controller to ensure proper signal connections
                        self.timeline_widget.set_controller(self)
                        print("DEBUG: Reconnected controller on timeline widget")

                # Call rebuild with animation
                self.timeline_widget.rebuild(animate_new=True)
                print("DEBUG: Called timeline_widget.rebuild(animate_new=True)")

                # Force immediate scene update
                if hasattr(self.timeline_widget, 'scene') and self.timeline_widget.scene:
                    self.timeline_widget.scene.update()
                    print("DEBUG: Called scene.update() for immediate refresh")

            except Exception as e:
                print(f"DEBUG: Error calling timeline_widget.rebuild(): {e}")
                import traceback
                traceback.print_exc()
        else:
            print("DEBUG: timeline_widget is None, cannot rebuild")

        # Обновить таблицу сегментов
        if self.segment_list_widget:
            print("DEBUG: Updating segment_list_widget")
            try:
                self.segment_list_widget.update_segments([marker.to_marker() for marker in self.project.markers])
            except Exception as e:
                print(f"DEBUG: Error updating segment_list_widget: {e}")
        else:
            print("DEBUG: segment_list_widget is None, cannot update")

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
        print(f"DEBUG: TimelineController.handle_hotkey called with hotkey: {hotkey}")
        print(f"DEBUG: custom_event_controller is {self.custom_event_controller}")

        # Найти событие по горячей клавише
        event_type = self._find_event_by_hotkey(hotkey)
        if not event_type:
            print(f"DEBUG: No event found for hotkey: {hotkey}")
            return

        print(f"DEBUG: Found event type: {event_type}")
        if self.settings.recording_mode == "dynamic":
            self._handle_dynamic_mode(event_type, current_frame, fps)
        elif self.settings.recording_mode == "fixed_length":
            self._handle_fixed_length_mode(event_type, current_frame, fps)

    def _find_event_by_hotkey(self, hotkey: str) -> str:
        """Найти тип события по горячей клавише."""
        print(f"DEBUG: _find_event_by_hotkey called with hotkey: {hotkey}")

        # Сначала проверить кастомные события через контроллер
        if self.custom_event_controller:
            all_events = self.custom_event_controller.get_all_events()
            print(f"DEBUG: Found {len(all_events)} custom events")
            for event in all_events:
                print(f"DEBUG: Checking event {event.name} with shortcut {event.shortcut}")
                if event.shortcut.upper() == hotkey.upper():
                    print(f"DEBUG: Found event {event.name} for hotkey {hotkey}")
                    return event.name

        # Затем проверить дефолтные события
        print(f"DEBUG: Checking {len(self.settings.default_events)} default events")
        for event in self.settings.default_events:
            print(f"DEBUG: Checking default event {event.name} with shortcut {event.shortcut}")
            if event.shortcut.upper() == hotkey.upper():
                print(f"DEBUG: Found default event {event.name} for hotkey {hotkey}")
                return event.name

        print(f"DEBUG: No event found for hotkey {hotkey}")
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
        # Генерация ID для нового маркера
        new_id = self._generate_marker_id()
        marker = Marker(
            id=new_id,
            start_frame=start_frame,
            end_frame=end_frame,
            event_name=event_name,
            note=note
        )

        command = AddMarkerCommand(self.project, marker)
        self.history_manager.execute_command(command)

        # Уведомить об изменении проекта
        self.project_modified.emit()

    def _generate_marker_id(self) -> int:
        """Сгенерировать уникальный ID для маркера."""
        if not self.project.markers:
            return 1
        
        # Найти максимальный ID и увеличить на 1
        max_id = max(marker.id for marker in self.project.markers)
        return max_id + 1

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
            # Если уже есть маркеры, нужно инициализировать их в новом виджете
            if self.project and self.project.markers:
                print(f"DEBUG: Initializing {len(self.project.markers)} existing markers in timeline widget")
                self.timeline_widget.set_markers(self.project.markers)

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
        print(f"DEBUG: TimelineController.init_tracks() called with total_frames={total_frames}")
        print(f"DEBUG: self.timeline_widget is {self.timeline_widget}")

        self.set_total_frames(total_frames)
        if self.timeline_widget is not None:
            print("DEBUG: Getting track names from event manager")
            # Get track names from event manager
            track_names = self._get_track_names()
            print(f"DEBUG: track_names={track_names}")
            self.timeline_widget.init_tracks(track_names, total_frames, self.fps)
            # Set initial markers
            print(f"DEBUG: Setting initial markers, count={len(self.project.markers)}")
            self.timeline_widget.set_markers(self.project.markers)
        else:
            print("DEBUG: timeline_widget is None, cannot init tracks")

    def _get_track_names(self) -> List[str]:
        """Get list of track names (event types) for timeline."""
        print("DEBUG: _get_track_names() called")

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
            print(f"DEBUG: event_manager is {event_manager}")
            if event_manager:
                custom_events = event_manager.get_all_events()
                print(f"DEBUG: custom_events count={len(custom_events)}")
                if custom_events:
                    # Use custom events + defaults for any missing
                    custom_names = [event.name for event in custom_events]
                    print(f"DEBUG: custom_names={custom_names}")
                    # Add defaults that aren't in custom
                    for default in default_tracks:
                        if default not in custom_names:
                            custom_names.append(default)
                    print(f"DEBUG: final track_names={custom_names}")
                    return custom_names
        except ImportError as e:
            print(f"DEBUG: ImportError in _get_track_names(): {e}")
            pass

        print(f"DEBUG: Using default tracks: {default_tracks}")
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
            old_marker = Marker(
                id=marker.id,
                start_frame=old_start,
                end_frame=old_end,
                event_name=old_event_name,
                note=old_note
            )
            new_marker = Marker(
                id=marker.id,
                start_frame=new_start,
                end_frame=new_end,
                event_name=new_event_name or old_event_name,
                note=new_note or old_note
            )
            command = ModifyMarkerCommand(self.project.markers, marker_idx, old_marker, new_marker)
            self.history_manager.execute_command(command)
            
            # Отправить сигнал об обновлении конкретного маркера
            self.marker_updated.emit(marker_idx)
            
            # Уведомить об изменении проекта
            self.project_modified.emit()

    def delete_marker(self, marker_idx: int):
        """Удалить маркер по индексу."""
        if 0 <= marker_idx < len(self.project.markers):
            marker = self.project.markers[marker_idx]
            
            # Создать команду удаления
            command = DeleteMarkerCommand(self.project, marker)
            self.history_manager.execute_command(command)
            
            # Уведомить об изменении проекта
            self.project_modified.emit()

    def get_selected_markers(self) -> List[int]:
        """Получить список индексов выделенных маркеров."""
        return list(self.selected_markers)

    def select_marker(self, marker_idx: int):
        """Выделить маркер."""
        if 0 <= marker_idx < len(self.project.markers):
            self.selected_markers.add(marker_idx)
            # Можно добавить визуальное выделение на таймлайне

    def deselect_marker(self, marker_idx: int):
        """Снять выделение с маркера."""
        self.selected_markers.discard(marker_idx)

    def clear_selection(self):
        """Снять выделение со всех маркеров."""
        self.selected_markers.clear()

    def toggle_marker_selection(self, marker_idx: int):
        """Переключить выделение маркера."""
        if 0 <= marker_idx < len(self.project.markers):
            if marker_idx in self.selected_markers:
                self.deselect_marker(marker_idx)
            else:
                self.select_marker(marker_idx)

    def handle_marker_selection(self, marker_idx: int, toggle_mode: bool = True):
        """Обработать выбор маркера на таймлайне.

        Args:
            marker_idx: Индекс маркера
            toggle_mode: Если True, переключает выделение. Если False, выделяет только этот маркер.
        """
        if 0 <= marker_idx < len(self.project.markers):
            if toggle_mode:
                self.toggle_marker_selection(marker_idx)
            else:
                # Выделить только этот маркер
                self.clear_selection()
                self.select_marker(marker_idx)
            
            # Обновить фильтрацию по выбранным маркерам
            self._update_selected_markers_filter()

    def select_single_marker(self, marker_idx: int):
        """Select a single marker and activate selected markers filter mode.
        
        Args:
            marker_idx: Index of the marker to select
        """
        if 0 <= marker_idx < len(self.project.markers):
            # Clear all selections first
            self.clear_selection()
            # Select the specific marker
            self.select_marker(marker_idx)
            # Activate selected markers filter mode
            self._activate_selected_markers_filter_mode()
            # Update UI to show only selected markers
            self._update_markers_display()

    def _activate_selected_markers_filter_mode(self):
        """Activate filter mode to show only selected markers."""
        if self.filter_controller:
            # Get selected marker IDs
            selected_ids = set()
            for idx in self.selected_markers:
                if 0 <= idx < len(self.project.markers):
                    selected_ids.add(self.project.markers[idx].id)
            
            # Set filter controller to show only selected markers
            self.filter_controller.set_selected_markers_filter(selected_ids)
            
            # Synchronize selection across components
            self._sync_timeline_selection()
            self._sync_segment_list_selection()

    def clear_selected_markers_filter_mode(self):
        """Clear selected markers filter mode and show all markers."""
        if self.filter_controller:
            self.filter_controller.clear_selected_markers_filter()
            self.clear_selection()
            self._update_markers_display()

    def toggle_selected_markers_filter_mode(self):
        """Toggle between showing all markers and only selected markers."""
        if self.filter_controller:
            if self.filter_controller.is_selected_markers_mode_active():
                self.clear_selected_markers_filter_mode()
            else:
                # If no markers selected, select current marker
                if not self.selected_markers and self.project.markers:
                    self.select_single_marker(0)
                else:
                    self._activate_selected_markers_filter_mode()

    def get_filtered_markers(self) -> List[Marker]:
        """Получить отфильтрованные маркеры."""
        if self.filter_controller:
            return self.filter_controller.filter_markers(self.project.markers)
        return self.project.markers

    def set_selected_markers_filter(self, marker_ids: set):
        """Установить фильтр по выбранным маркерам."""
        if self.filter_controller:
            self.filter_controller.set_selected_markers_filter(marker_ids)
            self._update_markers_display()

    def _update_selected_markers_filter(self):
        """Обновить фильтрацию по выбранным маркерам."""
        if self.filter_controller:
            # Получаем ID выделенных маркеров
            selected_ids = set()
            for idx in self.selected_markers:
                if 0 <= idx < len(self.project.markers):
                    selected_ids.add(self.project.markers[idx].id)
            
            # Устанавливаем фильтр выбранных маркеров
            self.filter_controller.set_selected_markers_filter(selected_ids)
            
            # Синхронизируем выделение на таймлайне
            self._sync_timeline_selection()
            
            # Синхронизируем выделение в списке сегментов
            self._sync_segment_list_selection()

    def _sync_timeline_selection(self):
        """Синхронизировать выделение маркеров на таймлайне."""
        if self.timeline_widget and hasattr(self.timeline_widget, 'scene'):
            scene = self.timeline_widget.scene
            if hasattr(scene, 'items'):
                # Сначала снимаем выделение со всех сегментов
                for item in scene.items():
                    if isinstance(item, QGraphicsRectItem) and hasattr(item, 'set_selected'):
                        item.set_selected(False)
                
                # Затем выделяем только выбранные маркеры
                for idx in self.selected_markers:
                    if 0 <= idx < len(self.project.markers):
                        marker = self.project.markers[idx]
                        # Находим соответствующий графический элемент
                        for item in scene.items():
                            if (isinstance(item, QGraphicsRectItem) and 
                                hasattr(item, 'marker') and 
                                item.marker.id == marker.id):
                                item.set_selected(True)
                                break

    def _sync_segment_list_selection(self):
        """Синхронизировать выделение маркеров в списке сегментов."""
        if self.segment_list_widget and hasattr(self.segment_list_widget, 'table'):
            table = self.segment_list_widget.table
            
            # Сначала снимаем выделение со всех строк
            table.clearSelection()
            
            # Затем выделяем строки для выбранных маркеров
            for idx in self.selected_markers:
                if 0 <= idx < table.rowCount():
                    # Проверяем, что в строке действительно находится нужный маркер
                    item = table.item(idx, 0)
                    if item and item.data(Qt.ItemDataRole.UserRole) == idx:
                        table.selectRow(idx)

    def save_project(self):
        """Сохранить проект через main controller."""
        if hasattr(self, '_main_controller') and self._main_controller:
            self._main_controller._on_save_project()

    def load_project(self):
        """Загрузить проект через main controller."""
        if hasattr(self, '_main_controller') and self._main_controller:
            self._main_controller._on_load_project()

    def new_project(self):
        """Создать новый проект через main controller."""
        if hasattr(self, '_main_controller') and self._main_controller:
            self._main_controller._on_new_project()

    def _on_filters_changed(self):
        """Обработка изменения фильтров из FilterController."""
        # Обновить отображение маркеров в соответствии с новыми фильтрами
        self._update_markers_display()

    def _update_markers_display(self):
        """Обновить отображение маркеров с учетом текущих фильтров."""
        if not hasattr(self, 'filter_controller'):
            return

        # Get all markers from project
        all_markers = self.project.markers
        
        # Apply filters using FilterController
        filtered_markers = self.filter_controller.filter_markers(all_markers)
        
        # Update timeline widget with filtered markers
        if self.timeline_widget and hasattr(self.timeline_widget, 'set_markers'):
            self.timeline_widget.set_markers(filtered_markers)

        # Update segment list widget with filtered markers
        if self.segment_list_widget:
            self.segment_list_widget.update_segments([marker.to_marker() for marker in filtered_markers])
