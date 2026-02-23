from __future__ import annotations

from dataclasses import replace
from typing import List, Optional, Set, Tuple, Dict

from PySide6.QtCore import Signal, QObject, Qt
from PySide6.QtWidgets import QGraphicsRectItem

from models.domain.marker import Marker
from models.domain.project import Project
from models.config.app_settings import AppSettings
from services.history import HistoryManager
from services.history.command_interface import Command
from views.widgets.segment_list import SegmentListWidget
from views.widgets.timeline_scene import TimelineWidget


# ──────────────────────────────────────────────────────────────────────────────
# History commands (FIXED)
# ──────────────────────────────────────────────────────────────────────────────

class AddMarkerCommand(Command):
    """Команда добавления маркера.

    Сохраняет индекс при execute, восстанавливает при undo.
    Redo (повторный execute) вставляет в тот же индекс.
    """

    def __init__(self, project: Project, marker: Marker):
        super().__init__(f"Add {marker.event_name} marker")
        self.project = project
        self.marker = marker
        self.index = -1

    def execute(self) -> None:
        if self.index < 0:
            self.index = len(self.project.markers)
        self.project.add_marker(self.marker, self.index)

    def undo(self) -> None:
        if 0 <= self.index < len(self.project.markers):
            self.project.remove_marker(self.index)


class ModifyMarkerCommand(Command):
    """Команда изменения маркера по индексу.

    FIX: Использует project.update_marker() вместо прямой записи
    в project.markers[idx], которая раньше писала в копию списка.
    """

    def __init__(self, project: Project, marker_idx: int,
                 old_marker: Marker, new_marker: Marker):
        super().__init__(f"Modify {new_marker.event_name} marker")
        self.project = project
        self.marker_idx = marker_idx
        self.old_marker = old_marker
        self.new_marker = new_marker

    def execute(self) -> None:
        if 0 <= self.marker_idx < len(self.project.markers):
            self.project.update_marker(self.marker_idx, self.new_marker)

    def undo(self) -> None:
        if 0 <= self.marker_idx < len(self.project.markers):
            self.project.update_marker(self.marker_idx, self.old_marker)


class DeleteMarkerCommand(Command):
    """Команда удаления маркера.

    FIX: Хранит marker_idx при создании, а не ищет через list.index().
    Раньше list.index() мог найти другой маркер при дубликатах,
    или бросить ValueError если маркер уже удалён.
    """

    def __init__(self, project: Project, marker_idx: int, marker: Marker):
        super().__init__(f"Delete {marker.event_name} marker")
        self.project = project
        self.marker_idx = marker_idx
        self.marker = marker

    def execute(self) -> None:
        if 0 <= self.marker_idx < len(self.project.markers):
            self.project.remove_marker(self.marker_idx)

    def undo(self) -> None:
        self.project.add_marker(self.marker, self.marker_idx)


# ──────────────────────────────────────────────────────────────────────────────
# TimelineController
# ──────────────────────────────────────────────────────────────────────────────

class TimelineController(QObject):
    """Контроллер управления маркерами + синхронизация с UI."""

    markers_changed = Signal()
    playback_time_changed = Signal(int)
    timeline_update = Signal()
    marker_updated = Signal(int)
    marker_selection_changed = Signal()

    project_modified = Signal()

    recording_state_changed = Signal(bool, str, int)

    def __init__(
        self,
        project: Project,
        timeline_widget: Optional[TimelineWidget],
        segment_list_widget: Optional[SegmentListWidget],
        history_manager: HistoryManager,
        settings: AppSettings,
        custom_event_controller=None,
    ):
        super().__init__()

        self.project = project
        self.timeline_widget = timeline_widget
        self.segment_list_widget = segment_list_widget
        self.history_manager = history_manager
        self.settings = settings
        self.custom_event_controller = custom_event_controller

        self._main_window = None
        self._main_controller = None

        self.playback_controller = None
        self.current_frame = 0
        self.fps = 30.0
        self.total_frames = 0

        self.recording_start_frame: Optional[int] = None
        self.is_recording: bool = False

        self.selected_markers: Set[int] = set()

        self.filter_controller = None

        self.project.marker_added.connect(self.on_marker_added)
        self.project.marker_removed.connect(self.on_marker_removed)
        self.project.markers_cleared.connect(self.on_markers_cleared)

        if self.timeline_widget is not None:
            self._connect_timeline_signals()

        self.markers_changed.connect(self._on_markers_changed_internal)

        if self.custom_event_controller is not None:
            self.custom_event_controller.events_changed.connect(self._on_events_changed)
            self.custom_event_controller.event_added.connect(self._on_event_added)
            self.custom_event_controller.event_deleted.connect(self._on_event_deleted)

    # ──────────────────────────────────────────────────────────────────────────
    # Dependency injection helpers
    # ──────────────────────────────────────────────────────────────────────────

    def set_main_window(self, window) -> None:
        self._main_window = window

    def set_main_controller(self, controller) -> None:
        self._main_controller = controller

    def set_playback_controller(self, playback_controller) -> None:
        self.playback_controller = playback_controller

    def set_custom_event_controller(self, custom_event_controller) -> None:
        self.custom_event_controller = custom_event_controller
        if self.custom_event_controller is not None:
            self.custom_event_controller.events_changed.connect(self._on_events_changed)
            self.custom_event_controller.event_added.connect(self._on_event_added)
            self.custom_event_controller.event_deleted.connect(self._on_event_deleted)

    def set_filter_controller(self, filter_controller) -> None:
        self.filter_controller = filter_controller
        if self.filter_controller is not None:
            self.filter_controller.filters_changed.connect(self._on_filters_changed)

    # ──────────────────────────────────────────────────────────────────────────
    # Project marker signals
    # ──────────────────────────────────────────────────────────────────────────

    def on_marker_added(self, index: int, marker: Marker) -> None:
        if self.timeline_widget:
            try:
                if hasattr(self.timeline_widget, "rebuild"):
                    self.timeline_widget.rebuild(animate_new=True)
                elif hasattr(self.timeline_widget, "set_markers"):
                    self.timeline_widget.set_markers(self.project.markers)
            except Exception as e:
                print(f"Timeline rebuild failed: {e}")

        self._update_markers_display()

    def on_marker_removed(self, index: int) -> None:
        self.markers_changed.emit()

    def on_marker_changed(self, index: int, marker: Marker) -> None:
        self.markers_changed.emit()

    def on_markers_cleared(self) -> None:
        self.markers_changed.emit()

    @property
    def markers(self) -> List[Marker]:
        return self.project.markers

    # ──────────────────────────────────────────────────────────────────────────
    # Undo / Redo (convenience wrappers)
    # ──────────────────────────────────────────────────────────────────────────

    def undo(self) -> None:
        """Отменить последнее действие."""
        if self.history_manager.undo():
            self.refresh_view()
            self.project_modified.emit()

    def redo(self) -> None:
        """Повторить отменённое действие."""
        if self.history_manager.redo():
            self.refresh_view()
            self.project_modified.emit()

    # ──────────────────────────────────────────────────────────────────────────
    # Hotkeys / recording modes
    # ──────────────────────────────────────────────────────────────────────────

    def handle_hotkey(self, hotkey: str, current_frame: int, fps: float) -> None:
        event_name = self._find_event_by_hotkey(hotkey)
        if not event_name:
            return

        if self.settings.recording_mode == "dynamic":
            self._handle_dynamic_mode(event_name, current_frame, fps)
        elif self.settings.recording_mode == "fixed_length":
            self._handle_fixed_length_mode(event_name, current_frame, fps)

    def _find_event_by_hotkey(self, hotkey: str) -> Optional[str]:
        if self.custom_event_controller:
            for event in self.custom_event_controller.get_all_events():
                if (event.shortcut or "").upper() == hotkey.upper():
                    return event.name

        for event in getattr(self.settings, "default_events", []):
            if (event.shortcut or "").upper() == hotkey.upper():
                return event.name

        return None

    def _handle_dynamic_mode(self, event_name: str, current_frame: int, fps: float) -> None:
        if not self.is_recording:
            self.recording_start_frame = current_frame
            self.is_recording = True
            self.recording_state_changed.emit(True, event_name, current_frame)
            return

        if self.recording_start_frame is None:
            self.is_recording = False
            self.recording_state_changed.emit(False, "", 0)
            return

        start_frame = self.recording_start_frame
        end_frame = current_frame

        start_frame = max(0, start_frame - int(self.settings.pre_roll_sec * fps))
        end_frame = end_frame + int(self.settings.post_roll_sec * fps)

        self.add_marker(start_frame, end_frame, event_name)

        self.recording_start_frame = None
        self.is_recording = False
        self.recording_state_changed.emit(False, "", 0)

    def _handle_fixed_length_mode(self, event_name: str, current_frame: int, fps: float) -> None:
        start_frame = current_frame - int(self.settings.pre_roll_sec * fps)
        end_frame = start_frame + int(self.settings.fixed_duration_sec * fps) + int(self.settings.post_roll_sec * fps)
        start_frame = max(0, start_frame)
        self.add_marker(start_frame, end_frame, event_name)

    # ──────────────────────────────────────────────────────────────────────────
    # CRUD markers with history (FIXED)
    # ──────────────────────────────────────────────────────────────────────────

    def add_marker(self, start_frame: int, end_frame: int, event_name: str, note: str = "") -> None:
        new_id = self._generate_marker_id()
        marker = Marker(
            id=new_id,
            start_frame=start_frame,
            end_frame=end_frame,
            event_name=event_name,
            note=note,
        )

        self.history_manager.execute_command(AddMarkerCommand(self.project, marker))
        self.project_modified.emit()

    def delete_marker(self, marker_idx: int) -> None:
        """Удалить маркер по оригинальному индексу.

        FIX: Передаём marker_idx в DeleteMarkerCommand вместо поиска
        через list.index() — это надёжнее при дубликатах и undo/redo.
        """
        if 0 <= marker_idx < len(self.project.markers):
            marker = self.project.markers[marker_idx]
            self.history_manager.execute_command(
                DeleteMarkerCommand(self.project, marker_idx, marker)
            )
            self.project_modified.emit()

    def duplicate_marker(self, marker_idx: int) -> None:
        """Дублировать маркер — создать копию с новым ID.

        Копия добавляется сразу после оригинала.
        """
        if not (0 <= marker_idx < len(self.project.markers)):
            return

        original = self.project.markers[marker_idx]
        new_id = self._generate_marker_id()

        duplicate = Marker(
            id=new_id,
            start_frame=original.start_frame,
            end_frame=original.end_frame,
            event_name=original.event_name,
            note=f"{original.note} (копия)" if original.note else "(копия)",
        )

        self.history_manager.execute_command(AddMarkerCommand(self.project, duplicate))
        self.project_modified.emit()

    def update_marker_optimized(
        self,
        marker_idx: int,
        new_start: int,
        new_end: int,
        new_event_name: Optional[str] = None,
        new_note: Optional[str] = None,
    ) -> None:
        """Изменить маркер с записью в историю.

        FIX: Использует project.update_marker() через ModifyMarkerCommand.
        """
        if not (0 <= marker_idx < len(self.project.markers)):
            return

        old_marker = self.project.markers[marker_idx]
        new_marker = Marker(
            id=old_marker.id,
            start_frame=new_start,
            end_frame=new_end,
            event_name=new_event_name if new_event_name is not None else old_marker.event_name,
            note=new_note if new_note is not None else old_marker.note,
        )

        self.history_manager.execute_command(
            ModifyMarkerCommand(self.project, marker_idx, old_marker, new_marker)
        )

        self.marker_updated.emit(marker_idx)
        self.project_modified.emit()

    def _generate_marker_id(self) -> int:
        if not self.project.markers:
            return 1
        return max(m.id for m in self.project.markers) + 1

    # ──────────────────────────────────────────────────────────────────────────
    # Playback sync / seeking
    # ──────────────────────────────────────────────────────────────────────────

    def seek_frame(self, frame_idx: int, update_playback: bool = True) -> None:
        if self.total_frames > 0:
            self.current_frame = max(0, min(frame_idx, self.total_frames - 1))
        else:
            self.current_frame = max(0, frame_idx)

        if self.timeline_widget and hasattr(self.timeline_widget, "set_current_frame"):
            self.timeline_widget.set_current_frame(self.current_frame, self.fps)

        if update_playback and self.playback_controller:
            self.playback_controller.seek_to_frame(self.current_frame)

        self.playback_time_changed.emit(self.current_frame)

    def set_fps(self, fps: float) -> None:
        self.fps = fps

    def set_total_frames(self, total_frames: int) -> None:
        self.total_frames = total_frames

    # ──────────────────────────────────────────────────────────────────────────
    # Timeline widget connections
    # ──────────────────────────────────────────────────────────────────────────

    def set_timeline_widget(self, timeline_widget: TimelineWidget) -> None:
        self.timeline_widget = timeline_widget
        if self.timeline_widget is not None:
            self._connect_timeline_signals()
            if self.project and self.project.markers and hasattr(self.timeline_widget, "set_markers"):
                self.timeline_widget.set_markers(self.project.markers)

    def _connect_timeline_signals(self) -> None:
        if self.timeline_widget is None:
            return

        if hasattr(self.timeline_widget, "scene") and hasattr(self.timeline_widget.scene, "seek_requested"):
            self.timeline_widget.scene.seek_requested.connect(self._on_timeline_seek)

            if hasattr(self.timeline_widget.scene, "event_double_clicked"):
                self.timeline_widget.scene.event_double_clicked.connect(self._on_event_double_clicked)

            if hasattr(self.timeline_widget.scene, "event_selected"):
                self.timeline_widget.scene.event_selected.connect(self._on_event_selected)

        elif hasattr(self.timeline_widget, "seek_requested"):
            self.timeline_widget.seek_requested.connect(self._on_timeline_seek)

            if hasattr(self.timeline_widget, "segment_edit_requested"):
                self.timeline_widget.segment_edit_requested.connect(self._on_event_double_clicked)

        # === НОВОЕ: Подключение сигналов контекстного меню ===
        if hasattr(self.timeline_widget, "context_edit_requested"):
            self.timeline_widget.context_edit_requested.connect(self._on_context_edit)
        if hasattr(self.timeline_widget, "context_delete_requested"):
            self.timeline_widget.context_delete_requested.connect(self._on_context_delete)
        if hasattr(self.timeline_widget, "context_duplicate_requested"):
            self.timeline_widget.context_duplicate_requested.connect(self._on_context_duplicate)
        if hasattr(self.timeline_widget, "context_jump_requested"):
            self.timeline_widget.context_jump_requested.connect(self._on_context_jump)
        if hasattr(self.timeline_widget, "context_export_requested"):
            self.timeline_widget.context_export_requested.connect(self._on_context_export)

    # === НОВЫЕ ОБРАБОТЧИКИ контекстного меню ===

    def _on_context_edit(self, marker_idx: int) -> None:
        """Редактировать маркер из контекстного меню."""
        self.edit_marker_requested(marker_idx)

    def _on_context_delete(self, marker_idx: int) -> None:
        """Удалить маркер из контекстного меню."""
        self.delete_marker(marker_idx)

    def _on_context_duplicate(self, marker_idx: int) -> None:
        """Дублировать маркер из контекстного меню."""
        self.duplicate_marker(marker_idx)

    def _on_context_jump(self, marker_idx: int) -> None:
        """Перейти к началу маркера из контекстного меню."""
        if 0 <= marker_idx < len(self.project.markers):
            marker = self.project.markers[marker_idx]
            self.seek_frame(marker.start_frame)

    def _on_context_export(self, marker_idx: int) -> None:
        """Экспортировать один клип из контекстного меню."""
        if self._main_controller and hasattr(self._main_controller, 'export_single_clip'):
            self._main_controller.export_single_clip(marker_idx)
        elif self._main_controller and hasattr(self._main_controller, '_on_export'):
            # Fallback: открыть общий диалог экспорта
            self._main_controller._on_export()

    def _on_timeline_seek(self, frame: int) -> None:
        self.seek_frame(frame)

    def _on_event_selected(self, marker: Marker) -> None:
        try:
            marker_idx = self.project.markers.index(marker)
        except ValueError:
            return

        self.clear_selection()
        self.select_marker(marker_idx)
        self._update_selected_markers_filter()
        self.marker_selection_changed.emit()

    def _on_event_double_clicked(self, marker: Marker) -> None:
        try:
            marker_idx = self.project.markers.index(marker)
        except ValueError:
            return
        self.edit_marker_requested(marker_idx)

    def edit_marker_requested(self, marker_idx: int) -> None:
        if self._main_window:
            self._main_window.open_segment_editor(marker_idx)

    # ──────────────────────────────────────────────────────────────────────────
    # Tracks init
    # ──────────────────────────────────────────────────────────────────────────

    def init_tracks(self, total_frames: int) -> None:
        self.set_total_frames(total_frames)

        if self.timeline_widget is None:
            return

        track_names = self._get_track_names()
        if hasattr(self.timeline_widget, "init_tracks"):
            self.timeline_widget.init_tracks(track_names, total_frames, self.fps)

        if hasattr(self.timeline_widget, "set_markers"):
            self.timeline_widget.set_markers(self.project.markers)

    def _get_track_names(self) -> List[str]:
        default_tracks = [
            "Заблокировано", "Блокшот в обороне", "Вброс", "Вбрасывание: Пропущено",
            "Вбрасывание: Проиграно", "Гол", "Бросок мимо", "Удаление",
            "Бросок в створ", "Перехват", "Потеря", "Вход в зону", "Выход из зоны"
        ]

        try:
            from services.events.custom_event_manager import get_custom_event_manager
            event_manager = get_custom_event_manager()
            if event_manager:
                events = event_manager.get_all_events()
                if events:
                    names = [e.name for e in events]
                    for d in default_tracks:
                        if d not in names:
                            names.append(d)
                    return names
        except Exception:
            pass

        return default_tracks

    # ──────────────────────────────────────────────────────────────────────────
    # UI refresh
    # ──────────────────────────────────────────────────────────────────────────

    def refresh_view(self) -> None:
        self.markers_changed.emit()

        if self.timeline_widget and hasattr(self.timeline_widget, "rebuild"):
            self.timeline_widget.rebuild(animate_new=False)

        self._update_markers_display()

    def _on_markers_changed_internal(self) -> None:
        if self.timeline_widget and hasattr(self.timeline_widget, "set_markers"):
            self.timeline_widget.set_markers(self.project.markers)

        self._update_markers_display()

    # ──────────────────────────────────────────────────────────────────────────
    # Filtering integration
    # ──────────────────────────────────────────────────────────────────────────

    def _on_filters_changed(self) -> None:
        self._update_markers_display()

    def get_filtered_pairs(self) -> List[Tuple[int, Marker]]:
        if self.filter_controller is not None:
            return self.filter_controller.filter_markers(self.project.markers)
        return [(i, m) for i, m in enumerate(self.project.markers)]

    def get_filtered_markers(self) -> List[Marker]:
        return [m for _, m in self.get_filtered_pairs()]

    def _update_markers_display(self) -> None:
        filtered_pairs = self.get_filtered_pairs()
        filtered_markers = [m for _, m in filtered_pairs]

        # === НОВОЕ: Передаём маппинг индексов для контекстного меню ===
        if self.timeline_widget:
            index_map = {m.id: idx for idx, m in filtered_pairs}
            if hasattr(self.timeline_widget, "set_markers_with_indices"):
                self.timeline_widget.set_markers_with_indices(filtered_markers, index_map)
            elif hasattr(self.timeline_widget, "set_markers"):
                self.timeline_widget.set_markers(filtered_markers)

        if self.segment_list_widget:
            if hasattr(self.segment_list_widget, "set_segments"):
                self.segment_list_widget.set_segments(filtered_pairs)
            else:
                self.segment_list_widget.update_segments(filtered_markers)

        self._sync_timeline_selection()
        self._sync_segment_list_selection()

    # ──────────────────────────────────────────────────────────────────────────
    # Selection
    # ──────────────────────────────────────────────────────────────────────────

    def get_selected_markers(self) -> List[int]:
        return sorted(self.selected_markers)

    def select_marker(self, marker_idx: int) -> None:
        if 0 <= marker_idx < len(self.project.markers):
            self.selected_markers.add(marker_idx)

    def deselect_marker(self, marker_idx: int) -> None:
        self.selected_markers.discard(marker_idx)

    def clear_selection(self) -> None:
        self.selected_markers.clear()

    def toggle_marker_selection(self, marker_idx: int) -> None:
        if marker_idx in self.selected_markers:
            self.selected_markers.remove(marker_idx)
        else:
            self.select_marker(marker_idx)

    def handle_marker_selection(self, marker_idx: int, toggle_mode: bool = True) -> None:
        if not (0 <= marker_idx < len(self.project.markers)):
            return

        if toggle_mode:
            self.toggle_marker_selection(marker_idx)
        else:
            self.clear_selection()
            self.select_marker(marker_idx)

        self._update_selected_markers_filter()
        self.marker_selection_changed.emit()

    def select_single_marker(self, marker_idx: int) -> None:
        if not (0 <= marker_idx < len(self.project.markers)):
            return

        self.clear_selection()
        self.select_marker(marker_idx)
        self._update_selected_markers_filter()
        self._update_markers_display()

    def clear_selected_markers_filter_mode(self) -> None:
        if self.filter_controller is None:
            return
        self.filter_controller.set_selected_marker_ids(set())
        self.clear_selection()
        self._update_markers_display()

    def toggle_selected_markers_filter_mode(self) -> None:
        if self.filter_controller is None:
            return
        if self.filter_controller.selected_marker_ids:
            self.clear_selected_markers_filter_mode()
        else:
            if not self.selected_markers and self.project.markers:
                self.select_single_marker(0)
            else:
                self._update_selected_markers_filter()
                self._update_markers_display()

    def _update_selected_markers_filter(self) -> None:
        if self.filter_controller is None:
            return

        selected_ids = {
            self.project.markers[idx].id
            for idx in self.selected_markers
            if 0 <= idx < len(self.project.markers)
        }
        self.filter_controller.set_selected_marker_ids(selected_ids)

    # ──────────────────────────────────────────────────────────────────────────
    # Selection sync to widgets
    # ──────────────────────────────────────────────────────────────────────────

    def _sync_timeline_selection(self) -> None:
        if not self.timeline_widget or not hasattr(self.timeline_widget, "scene"):
            return

        scene = self.timeline_widget.scene
        if not hasattr(scene, "items"):
            return

        selected_ids = {
            self.project.markers[idx].id
            for idx in self.selected_markers
            if 0 <= idx < len(self.project.markers)
        }

        for item in scene.items():
            if isinstance(item, QGraphicsRectItem) and hasattr(item, "marker") and hasattr(item, "set_selected"):
                item.set_selected(item.marker.id in selected_ids)

    def _sync_segment_list_selection(self) -> None:
        if not self.segment_list_widget:
            return

        table = self.segment_list_widget.table

        # === FIX: QTableView не имеет rowCount() — берём из модели ===
        model = table.model()
        if model is None:
            return

        table.blockSignals(True)
        try:
            table.clearSelection()

            selected_orig = set(self.selected_markers)
            selection_model = table.selectionModel()
            if selection_model is None:
                return

            for row in range(model.rowCount()):
                # === FIX: QTableView не имеет item() — берём через model.data() ===
                index = model.index(row, 0)
                orig_idx = model.data(index, Qt.ItemDataRole.UserRole)
                if orig_idx in selected_orig:
                    table.selectRow(row)
        finally:
            table.blockSignals(False)

    # ──────────────────────────────────────────────────────────────────────────
    # Custom events changes
    # ──────────────────────────────────────────────────────────────────────────

    def _on_events_changed(self) -> None:
        pass

    def _on_event_added(self, event) -> None:
        pass

    def _on_event_deleted(self, event_name: str) -> None:
        """Удалить все маркеры с этим event_name.

        FIX: Используем новый DeleteMarkerCommand с marker_idx.
        Удаляем в обратном порядке, чтобы индексы не сдвигались.
        """
        indices_to_remove = [
            i for i, m in enumerate(self.project.markers)
            if m.event_name == event_name
        ]
        if not indices_to_remove:
            return

        for idx in reversed(indices_to_remove):
            marker = self.project.markers[idx]
            self.history_manager.execute_command(
                DeleteMarkerCommand(self.project, idx, marker)
            )

        self.project_modified.emit()
        self.refresh_view()

    def get_total_frames(self) -> int:
        return self.total_frames

    def get_fps(self) -> float:
        return self.fps

    def get_current_frame_idx(self) -> int:
        return self.current_frame