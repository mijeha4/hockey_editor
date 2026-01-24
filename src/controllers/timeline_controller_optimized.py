"""Оптимизированный TimelineController с реактивными моделями данных.

Предоставляет высокопроизводительное обновление таймлайна с использованием
реактивных моделей ObservableMarker и ObservableProject.
"""

from typing import List, Dict, Optional, Callable
from PySide6.QtCore import Signal, QObject, QTimer

# Импорты моделей
from models.domain.marker import Marker
from models.domain.project import Project
from models.domain.observable_project import ObservableProject
from models.domain.observable_marker import ObservableMarker, ObservableMarkerList

# Импорты сервисов
from services.history import HistoryManager, Command
from models.config.app_settings import AppSettings

# Импорты виджетов
from views.widgets.segment_list import SegmentListWidget
from views.widgets.timeline import TimelineWidget

# Импорты команд
try:
    from utils.commands.modify_marker_command import ModifyMarkerCommand
    from utils.commands.delete_marker_command import DeleteMarkerCommand
except ImportError:
    # Для случаев, когда запускаем из src/
    try:
        from ..utils.commands.modify_marker_command import ModifyMarkerCommand
        from ..utils.commands.delete_marker_command import DeleteMarkerCommand
    except ImportError:
        # Fallback для тестирования
        from hockey_editor.utils.commands.modify_marker_command import ModifyMarkerCommand
        from hockey_editor.utils.commands.delete_marker_command import DeleteMarkerCommand


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


class OptimizedTimelineController(QObject):
    """Оптимизированный контроллер управления маркерами с реактивными моделями."""

    # Сигналы для UI обновления
    markers_changed = Signal()
    playback_time_changed = Signal(int)
    timeline_update = Signal()
    marker_updated = Signal(int)  # Индекс измененного маркера

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

        # Ссылка на главное окно для InstanceEditWindow
        self._main_window = None

        # Состояние для Dynamic режима
        self.recording_start_frame = None
        self.is_recording = False

        # Текущее состояние воспроизведения
        self.current_frame = 0
        self.fps = 30.0
        self.total_frames = 0

        # Ссылка на playback controller для синхронизации
        self.playback_controller = None

        # Реактивный проект (если используется)
        self.observable_project: Optional[ObservableProject] = None

        # Таймер для буферизации изменений
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._flush_pending_updates)
        self._pending_updates = []  # Очередь ожидающих обновлений

        # Флаг для предотвращения рекурсивных обновлений
        self._updating_ui = False

        # Подключить сигналы от View
        if self.timeline_widget is not None:
            self.timeline_widget.seek_requested.connect(self._on_timeline_seek)

        # Подключить сигналы от CustomEventController
        if self.custom_event_controller is not None:
            self.custom_event_controller.events_changed.connect(self._on_events_changed)
            self.custom_event_controller.event_added.connect(self._on_event_added)
            self.custom_event_controller.event_deleted.connect(self._on_event_deleted)

    def set_main_window(self, window):
        """Установить ссылку на главное окно."""
        self._main_window = window

    def set_playback_controller(self, playback_controller):
        """Установить ссылку на playback controller для синхронизации."""
        self.playback_controller = playback_controller

    def set_observable_project(self, observable_project: ObservableProject):
        """Установить реактивный проект и подключить сигналы."""
        # Отключить предыдущие сигналы
        self._disconnect_project_signals()
        
        self.observable_project = observable_project
        self.project = observable_project.to_project()  # Для совместимости
        
        # Подключить сигналы реактивного проекта
        self._connect_project_signals()
        self._connect_markers_signals()

        # Инициализировать UI с реактивными данными
        self._initialize_ui_with_observable_data()

    def _connect_project_signals(self):
        """Подключить сигналы реактивного проекта."""
        if self.observable_project:
            self.observable_project.markers_changed.connect(self._on_markers_changed_reactive)
            self.observable_project.marker_added.connect(self._on_marker_added_reactive)
            self.observable_project.marker_removed.connect(self._on_marker_removed_reactive)
            self.observable_project.marker_modified.connect(self._on_marker_modified_reactive)
            self.observable_project.project_modified.connect(self.project_modified)

    def _disconnect_project_signals(self):
        """Отключить сигналы реактивного проекта."""
        if self.observable_project:
            try:
                self.observable_project.markers_changed.disconnect(self._on_markers_changed_reactive)
                self.observable_project.marker_added.disconnect(self._on_marker_added_reactive)
                self.observable_project.marker_removed.disconnect(self._on_marker_removed_reactive)
                self.observable_project.marker_modified.disconnect(self._on_marker_modified_reactive)
                self.observable_project.project_modified.disconnect(self.project_modified)
            except TypeError:
                pass  # Сигналы не были подключены

    def _connect_markers_signals(self):
        """Подключить сигналы изменений маркеров."""
        if self.observable_project:
            for marker in self.observable_project.markers:
                marker.marker_changed.connect(self._on_marker_changed_reactive)

    def _disconnect_markers_signals(self):
        """Отключить сигналы изменений маркеров."""
        if self.observable_project:
            for marker in self.observable_project.markers:
                try:
                    marker.marker_changed.disconnect(self._on_marker_changed_reactive)
                except TypeError:
                    pass  # Сигнал не был подключен

    def _initialize_ui_with_observable_data(self):
        """Инициализировать UI с данными из реактивного проекта."""
        if self.observable_project:
            # Преобразовать ObservableMarkers в обычные Marker для совместимости
            regular_markers = [marker.to_marker() for marker in self.observable_project.markers]
            self.segment_list_widget.update_segments(regular_markers)
            
            # Установить сегменты в timeline widget
            if self.timeline_widget:
                self.timeline_widget.set_segments(regular_markers)

    def handle_hotkey(self, hotkey: str, current_frame: int, fps: float) -> None:
        """
        Обработка нажатия горячей клавиши с оптимизацией.

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
        """Добавить маркер с оптимизацией UI обновления."""
        marker = Marker(
            start_frame=start_frame,
            end_frame=end_frame,
            event_name=event_name,
            note=note
        )

        # Добавить в реактивный проект, если он используется
        if self.observable_project:
            observable_marker = ObservableMarker.from_marker(marker)
            self.observable_project.add_marker(observable_marker)
        else:
            # Добавить в обычный проект
            command = AddMarkerCommand(self.project, marker)
            self.history_manager.execute_command(command)

        # Оптимизированное обновление UI
        self._schedule_ui_update()

    def modify_marker(self, marker_idx: int, new_marker):
        """Изменить существующий маркер с оптимизацией."""
        if 0 <= marker_idx < len(self.project.markers):
            old_marker = self.project.markers[marker_idx]

            # Создать команду модификации
            command = ModifyMarkerCommand(self.project.markers, marker_idx, old_marker, new_marker)
            self.history_manager.execute_command(command)

            # Оптимизированное обновление UI
            self._schedule_ui_update(marker_idx=marker_idx)

    def delete_marker(self, marker_idx: int):
        """Удалить маркер с оптимизацией."""
        if 0 <= marker_idx < len(self.project.markers):
            marker = self.project.markers[marker_idx]

            # Создать команду удаления
            command = DeleteMarkerCommand(self.project.markers, marker_idx)
            self.history_manager.execute_command(command)

            # Оптимизированное обновление UI
            self._schedule_ui_update()

    def _schedule_ui_update(self, marker_idx: Optional[int] = None):
        """Запланировать оптимизированное обновление UI."""
        if self._updating_ui:
            return

        # Добавить в очередь обновлений
        self._pending_updates.append(marker_idx)
        self._update_timer.start(16)  # ~60 FPS

    def _flush_pending_updates(self):
        """Выполнить все запланированные обновления UI."""
        if not self._pending_updates or self._updating_ui:
            return

        self._updating_ui = True

        try:
            # Получить все ожидающие обновления
            updates = self._pending_updates.copy()
            self._pending_updates.clear()

            # Определить тип обновления
            if len(updates) == 1 and updates[0] is not None:
                # Частичное обновление одного маркера
                self._update_single_marker(updates[0])
            else:
                # Полное обновление (если несколько изменений или неизвестный тип)
                self._update_all_markers()

        finally:
            self._updating_ui = False

    def _update_single_marker(self, marker_idx: int):
        """Оптимизированное обновление одного маркера."""
        if marker_idx < 0 or marker_idx >= len(self.project.markers):
            return

        marker = self.project.markers[marker_idx]

        # Обновить segment list widget
        self.segment_list_widget.update_segments(self.project.markers)

        # Обновить timeline widget (оптимизированно)
        if self.timeline_widget:
            self.timeline_widget.update_segment_optimized(marker, marker_idx)

        # Отправить сигнал об обновлении конкретного маркера
        self.marker_updated.emit(marker_idx)
        self.project_modified.emit()

    def _update_all_markers(self):
        """Полное обновление всех маркеров."""
        # Обновить segment list widget
        self.segment_list_widget.update_segments(self.project.markers)

        # Обновить timeline widget
        if self.timeline_widget:
            self.timeline_widget.set_segments(self.project.markers)

        # Отправить сигнал об изменении маркеров
        self.markers_changed.emit()
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
        if self.timeline_widget:
            self.timeline_widget.set_segments(self.project.markers)

        # Обновить таблицу сегментов
        self.segment_list_widget.update_segments(self.project.markers)

    def set_timeline_widget(self, timeline_widget):
        """Установить timeline widget и подключить сигналы."""
        self.timeline_widget = timeline_widget

    def edit_marker_requested(self, marker_idx: int):
        """Обработка запроса на редактирование маркера."""
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
        print("OptimizedTimelineController: Events list changed, updating hotkey mappings")
        # Список событий изменился, но нам не нужно предпринимать специальных действий
        # OptimizedTimelineController будет использовать актуальный список при следующем вызове _find_event_by_hotkey

    def _on_event_added(self, event):
        """Обработка добавления нового события."""
        print(f"OptimizedTimelineController: New event added: {event.name} (shortcut: {event.shortcut})")
        # Новое событие добавлено, оно будет доступно при следующем поиске по горячим клавишам

    def _on_event_deleted(self, event_name: str):
        """Обработка удаления события."""
        print(f"OptimizedTimelineController: Event deleted: {event_name}")

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

        # Оптимизированное обновление UI
        if markers_to_remove:
            print(f"OptimizedTimelineController: Removed {len(markers_to_remove)} markers with deleted event '{event_name}'")
            self._schedule_ui_update()

    # --- Реактивные методы для Observable Project ---

    def _on_markers_changed_reactive(self):
        """Обработка изменения списка маркеров в реактивном проекте."""
        # Обновляем обычный project для совместимости
        self.project = self.observable_project.to_project()
        self._schedule_ui_update()

    def _on_marker_added_reactive(self, marker: ObservableMarker):
        """Обработка добавления маркера в реактивном проекте."""
        self.project = self.observable_project.to_project()
        # Найти индекс добавленного маркера
        marker_idx = len(self.project.markers) - 1
        self._schedule_ui_update(marker_idx=marker_idx)

    def _on_marker_removed_reactive(self, marker: ObservableMarker):
        """Обработка удаления маркера из реактивного проекта."""
        self.project = self.observable_project.to_project()
        self._schedule_ui_update()

    def _on_marker_modified_reactive(self, marker: ObservableMarker):
        """Обработка изменения маркера в реактивном проекте."""
        self.project = self.observable_project.to_project()
        # Найти индекс измененного маркера
        try:
            marker_idx = self.project.markers.index(marker.to_marker())
            self._schedule_ui_update(marker_idx=marker_idx)
        except ValueError:
            # Маркер не найден, сделать полное обновление
            self._schedule_ui_update()

    def _on_marker_changed_reactive(self):
        """Обработка изменения свойств маркера."""
        self.project = self.observable_project.to_project()
        self._schedule_ui_update()

    def add_observable_marker(self, start_frame: int, end_frame: int, event_name: str, note: str = ""):
        """Добавить маркер в реактивный проект."""
        if self.observable_project:
            marker = ObservableMarker(start_frame, end_frame, event_name, note)
            self.observable_project.add_marker(marker)
            
            # Создать команду для истории
            regular_marker = marker.to_marker()
            command = AddMarkerCommand(self.project, regular_marker)
            self.history_manager.execute_command(command)
        else:
            # Резервный вариант для обычного проекта
            self.add_marker(start_frame, end_frame, event_name, note)

    def modify_observable_marker(self, marker_idx: int, new_start: int, new_end: int, new_event_name: str, new_note: str):
        """Изменить маркер в реактивном проекте."""
        if self.observable_project:
            if 0 <= marker_idx < len(self.observable_project.markers):
                marker = self.observable_project.markers[marker_idx]
                
                # Создать команду для истории
                old_marker = marker.to_marker()
                new_marker = Marker(new_start, new_end, new_event_name, new_note)
                command = ModifyMarkerCommand(self.project.markers, marker_idx, old_marker, new_marker)
                self.history_manager.execute_command(command)
                
                # Применить изменения
                marker.start_frame = new_start
                marker.end_frame = new_end
                marker.event_name = new_event_name
                marker.note = new_note
        else:
            # Резервный вариант для обычного проекта
            if 0 <= marker_idx < len(self.project.markers):
                new_marker = Marker(new_start, new_end, new_event_name, new_note)
                self.modify_marker(marker_idx, new_marker)

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
            
            # Оптимизированное обновление UI
            self._schedule_ui_update(marker_idx=marker_idx)

    def undo(self):
        """Отменить последнюю команду."""
        if self.history_manager.undo():
            # Обновить UI после отмены
            self._schedule_ui_update()

    def redo(self):
        """Повторить последнюю отмененную команду."""
        if self.history_manager.redo():
            # Обновить UI после повтора
            self._schedule_ui_update()

    def get_filtered_segments(self) -> List[Marker]:
        """Получить отфильтрованные сегменты."""
        return self.segment_list_widget.get_filtered_segments()