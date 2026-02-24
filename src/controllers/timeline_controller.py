from __future__ import annotations

from typing import List, Optional, Set, Tuple, Dict

from PySide6.QtCore import Signal, QObject, Qt, QTimer
from PySide6.QtWidgets import QGraphicsRectItem

from models.domain.marker import Marker
from models.domain.project import Project
from models.config.app_settings import AppSettings
from services.history import HistoryManager
from services.history.command_interface import Command
from views.widgets.segment_list import SegmentListWidget
from views.widgets.timeline_scene import TimelineWidget


# ──────────────────────────────────────────────────────────────────────────────
# History commands
# ──────────────────────────────────────────────────────────────────────────────

class AddMarkerCommand(Command):
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


class BatchCommand(Command):
    def __init__(self, description: str, commands: List[Command]):
        super().__init__(description)
        self.commands = list(commands)

    def execute(self) -> None:
        for cmd in self.commands:
            cmd.execute()

    def undo(self) -> None:
        for cmd in reversed(self.commands):
            cmd.undo()


# ──────────────────────────────────────────────────────────────────────────────
# TimelineController
# ──────────────────────────────────────────────────────────────────────────────

class TimelineController(QObject):
    """Контроллер управления маркерами + синхронизация с UI.

    FIX: Все обновления UI проходят через debounce-таймер (_rebuild_timer),
    который объединяет несколько изменений в ОДНО перестроение сцены.
    Это предотвращает краш при быстром добавлении маркеров.
    """

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

        # ══════════════════════════════════════════════════════════════════════
        # FIX: Debounce timer — объединяет множественные rebuild в ОДИН
        # ══════════════════════════════════════════════════════════════════════
        self._rebuild_timer = QTimer(self)
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.setInterval(16)  # ~60fps — незаметная задержка
        self._rebuild_timer.timeout.connect(self._do_full_ui_update)

        # ── Connect project model signals ──
        self.project.marker_added.connect(self._on_project_changed)
        self.project.marker_removed.connect(self._on_project_changed_int)
        self.project.markers_cleared.connect(self._on_project_changed)
        if hasattr(self.project, "markers_replaced"):
            self.project.markers_replaced.connect(self._on_project_changed)

        # NOTE: Мы НЕ подключаем markers_changed → _on_markers_changed_internal.
        # Это убирает каскад из 3-4 перестроений. Вместо этого все обновления
        # проходят через _schedule_rebuild → _do_full_ui_update.

        if self.timeline_widget is not None:
            self._connect_timeline_signals()

        if self.custom_event_controller is not None:
            self.custom_event_controller.events_changed.connect(self._on_events_changed)
            self.custom_event_controller.event_added.connect(self._on_event_added)
            self.custom_event_controller.event_deleted.connect(self._on_event_deleted)

    # ──────────────────────────────────────────────────────────────────────────
    # FIX: Debounced rebuild
    # ──────────────────────────────────────────────────────────────────────────

    def _on_project_changed(self, *args) -> None:
        """Слот для сигналов project: marker_added, markers_cleared, markers_replaced."""
        self._schedule_rebuild()

    def _on_project_changed_int(self, index: int) -> None:
        """Слот для marker_removed(int)."""
        self._schedule_rebuild()

    def _schedule_rebuild(self) -> None:
        """Запланировать перестроение UI.

        Если вызвано несколько раз подряд (быстрые хоткеи),
        таймер НЕ перезапускается — первое перестроение произойдёт
        через 16мс после ПЕРВОГО вызова, а следующее — после следующего.
        """
        if not self._rebuild_timer.isActive():
            self._rebuild_timer.start()

    def _do_full_ui_update(self) -> None:
        """Единственная точка обновления всего UI.

        Вызывается либо по таймеру (deferred), либо напрямую из refresh_view().
        Гарантирует ОДНО перестроение сцены за вызов.
        """
        self._rebuild_timer.stop()  # Отменить pending, если вызван напрямую

        filtered_pairs = self.get_filtered_pairs()
        filtered_markers = [m for _, m in filtered_pairs]

        # 1. Обновить timeline scene (ОДНО перестроение)
        if self.timeline_widget:
            index_map = {m.id: idx for idx, m in filtered_pairs}
            if hasattr(self.timeline_widget, "set_markers_with_indices"):
                self.timeline_widget.set_markers_with_indices(filtered_markers, index_map)
            elif hasattr(self.timeline_widget, "set_markers"):
                self.timeline_widget.set_markers(filtered_markers)

        # 2. Обновить segment list
        if self.segment_list_widget:
            if hasattr(self.segment_list_widget, "set_segments"):
                self.segment_list_widget.set_segments(filtered_pairs)
            else:
                self.segment_list_widget.update_segments(filtered_markers)

        # 3. Синхронизировать выделение (после rebuild — items валидны)
        self._sync_timeline_selection()
        self._sync_segment_list_selection()

        # 4. Уведомить внешних слушателей (stats widget, tab title, и т.д.)
        self.markers_changed.emit()

    # ──────────────────────────────────────────────────────────────────────────
    # Toast helper
    # ──────────────────────────────────────────────────────────────────────────

    def _notify(self, message: str, level: str = "success", **kwargs) -> None:
        try:
            mc = self._main_controller
            if mc is None:
                return
            mw = getattr(mc, "main_window", None)
            if mw is None:
                return
            method = getattr(mw, f"show_toast_{level}", None)
            if method:
                method(message, **kwargs)
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────────────────
    # Dependency injection
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
    # Markers property
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def markers(self) -> List[Marker]:
        return self.project.markers

    # ──────────────────────────────────────────────────────────────────────────
    # Undo / Redo
    # ──────────────────────────────────────────────────────────────────────────

    def undo(self) -> None:
        desc = self.history_manager.undo()
        if desc:
            self.refresh_view()
            self.project_modified.emit()

    def redo(self) -> None:
        desc = self.history_manager.redo()
        if desc:
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
            self._notify(f"⏺ Запись: {event_name}", "info", duration_ms=1500)
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
        end_frame = start_frame + int(self.settings.fixed_duration_sec * fps) + int(
            self.settings.post_roll_sec * fps)
        start_frame = max(0, start_frame)
        self.add_marker(start_frame, end_frame, event_name)

    # ──────────────────────────────────────────────────────────────────────────
    # CRUD markers with history
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
        self._notify(f"✅ {event_name}", "success", duration_ms=2000)

    def delete_marker(self, marker_idx: int) -> None:
        if 0 <= marker_idx < len(self.project.markers):
            marker = self.project.markers[marker_idx]
            event_name = marker.event_name

            self.history_manager.execute_command(
                DeleteMarkerCommand(self.project, marker_idx, marker)
            )
            self.project_modified.emit()

            self._notify(
                f"Удалён: {event_name}",
                "warning",
                duration_ms=4000,
                action_text="Отмена",
                action_callback=lambda: self.undo(),
            )

    def duplicate_marker(self, marker_idx: int) -> None:
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
        self._notify(f"Дублирован: {original.event_name}", "success", duration_ms=2000)

    def update_marker_optimized(
        self,
        marker_idx: int,
        new_start: int,
        new_end: int,
        new_event_name: Optional[str] = None,
        new_note: Optional[str] = None,
    ) -> None:
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

    # ──────────────────────────────────────────────────────────────────────────
    # Batch operations
    # ──────────────────────────────────────────────────────────────────────────

    def batch_delete_markers(self, marker_indices: List[int]) -> None:
        sorted_indices = sorted(marker_indices, reverse=True)

        commands: List[Command] = []
        for idx in sorted_indices:
            if 0 <= idx < len(self.project.markers):
                marker = self.project.markers[idx]
                commands.append(DeleteMarkerCommand(self.project, idx, marker))

        if not commands:
            return

        batch = BatchCommand(f"Delete {len(commands)} markers", commands)
        self.history_manager.execute_command(batch)
        self.project_modified.emit()

        count = len(commands)
        self._notify(
            f"Удалено: {count} маркеров", "warning", duration_ms=5000,
            action_text="Отмена", action_callback=lambda: self.undo(),
        )

    def batch_change_event_type(self, marker_indices: List[int], new_event_name: str) -> None:
        commands: List[Command] = []

        for idx in sorted(marker_indices):
            if not (0 <= idx < len(self.project.markers)):
                continue

            old_marker = self.project.markers[idx]
            if old_marker.event_name == new_event_name:
                continue

            new_marker = Marker(
                id=old_marker.id,
                start_frame=old_marker.start_frame,
                end_frame=old_marker.end_frame,
                event_name=new_event_name,
                note=old_marker.note,
            )
            commands.append(ModifyMarkerCommand(self.project, idx, old_marker, new_marker))

        if not commands:
            return

        batch = BatchCommand(f"Change {len(commands)} markers to '{new_event_name}'", commands)
        self.history_manager.execute_command(batch)
        self.project_modified.emit()
        self._notify(f"Изменён тип: {len(commands)} → {new_event_name}", "success", duration_ms=2500)

    def batch_duplicate_markers(self, marker_indices: List[int]) -> None:
        commands: List[Command] = []

        for idx in sorted(marker_indices):
            if not (0 <= idx < len(self.project.markers)):
                continue

            original = self.project.markers[idx]
            new_id = self._generate_marker_id() + len(commands)

            duplicate = Marker(
                id=new_id,
                start_frame=original.start_frame,
                end_frame=original.end_frame,
                event_name=original.event_name,
                note=f"{original.note} (копия)" if original.note else "(копия)",
            )
            commands.append(AddMarkerCommand(self.project, duplicate))

        if not commands:
            return

        batch = BatchCommand(f"Duplicate {len(commands)} markers", commands)
        self.history_manager.execute_command(batch)
        self.project_modified.emit()
        self._notify(f"Дублировано: {len(commands)} маркеров", "success", duration_ms=2500)

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

    def _on_context_edit(self, marker_idx: int) -> None:
        self.edit_marker_requested(marker_idx)

    def _on_context_delete(self, marker_idx: int) -> None:
        self.delete_marker(marker_idx)

    def _on_context_duplicate(self, marker_idx: int) -> None:
        self.duplicate_marker(marker_idx)

    def _on_context_jump(self, marker_idx: int) -> None:
        if 0 <= marker_idx < len(self.project.markers):
            marker = self.project.markers[marker_idx]
            self.seek_frame(marker.start_frame)

    def _on_context_export(self, marker_idx: int) -> None:
        if self._main_controller and hasattr(self._main_controller, 'export_single_clip'):
            self._main_controller.export_single_clip(marker_idx)
        elif self._main_controller and hasattr(self._main_controller, '_on_export'):
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
    # UI refresh — FIX: единственная точка входа
    # ──────────────────────────────────────────────────────────────────────────

    def refresh_view(self) -> None:
        """Немедленное обновление UI (для undo/redo, load project и т.д.)."""
        self._do_full_ui_update()

    # ──────────────────────────────────────────────────────────────────────────
    # Filtering
    # ──────────────────────────────────────────────────────────────────────────

    def _on_filters_changed(self) -> None:
        self._do_full_ui_update()

    def get_filtered_pairs(self) -> List[Tuple[int, Marker]]:
        if self.filter_controller is not None:
            return self.filter_controller.filter_markers(self.project.markers)
        return [(i, m) for i, m in enumerate(self.project.markers)]

    def get_filtered_markers(self) -> List[Marker]:
        return [m for _, m in self.get_filtered_pairs()]

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
        self._do_full_ui_update()

    def clear_selected_markers_filter_mode(self) -> None:
        if self.filter_controller is None:
            return
        self.filter_controller.set_selected_marker_ids(set())
        self.clear_selection()
        self._do_full_ui_update()

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
                self._do_full_ui_update()

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
    # Selection sync — FIX: проверяем _is_rebuilding
    # ──────────────────────────────────────────────────────────────────────────

    def _sync_timeline_selection(self) -> None:
        if not self.timeline_widget or not hasattr(self.timeline_widget, "scene"):
            return

        scene = self.timeline_widget.scene
        if not hasattr(scene, "items"):
            return

        # FIX: не итерировать items во время rebuild
        if getattr(scene, '_is_rebuilding', False):
            return

        selected_ids = {
            self.project.markers[idx].id
            for idx in self.selected_markers
            if 0 <= idx < len(self.project.markers)
        }

        try:
            for item in scene.items():
                if (isinstance(item, QGraphicsRectItem)
                        and hasattr(item, "marker")
                        and hasattr(item, "set_selected")):
                    item.set_selected(item.marker.id in selected_ids)
        except RuntimeError:
            # Scene items могли быть удалены между итерациями
            pass

    def _sync_segment_list_selection(self) -> None:
        if not self.segment_list_widget:
            return

        table = self.segment_list_widget.table
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
                index = model.index(row, 0)
                orig_idx = model.data(index, Qt.ItemDataRole.UserRole)
                if orig_idx in selected_orig:
                    table.selectRow(row)
        except RuntimeError:
            pass
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
        indices_to_remove = [
            i for i, m in enumerate(self.project.markers)
            if m.event_name == event_name
        ]
        if not indices_to_remove:
            return

        commands: List[Command] = []
        for idx in reversed(indices_to_remove):
            marker = self.project.markers[idx]
            commands.append(DeleteMarkerCommand(self.project, idx, marker))

        batch = BatchCommand(
            f"Delete all '{event_name}' markers ({len(commands)})",
            commands,
        )
        self.history_manager.execute_command(batch)

        self.project_modified.emit()
        self.refresh_view()

        self._notify(
            f"Удалены маркеры: {event_name} ({len(commands)} шт.)",
            "warning", duration_ms=4000,
            action_text="Отмена",
            action_callback=lambda: self.undo(),
        )

    def get_total_frames(self) -> int:
        return self.total_frames

    def get_fps(self) -> float:
        return self.fps

    def get_current_frame_idx(self) -> int:
        return self.current_frame