"""
Main Controller - главный контроллер одного окна приложения.
"""

from __future__ import annotations

from typing import Optional, List

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from models.domain.project import Project
from models.config.app_settings import AppSettings
from services.video_engine import VideoService
from services.history import HistoryManager, get_history_manager
from services.serialization import ProjectIO

from views.windows.main_window import MainWindow
from views.windows.settings_dialog import SettingsDialog

from controllers.playback_controller import PlaybackController
from controllers.timeline_controller import TimelineController
from controllers.project_controller import ProjectController
from controllers.export import ExportController
from controllers.shortcut_controller import ShortcutController
from controllers.filter_controller import FilterController
from controllers.instance_edit_controller import InstanceEditController
from controllers.settings_controller import SettingsController
from controllers.custom_event_controller import CustomEventController

from controllers.application_controller import get_application_controller

try:
    from views.dialogs.new_project_dialog import NewProjectDialog
    from views.dialogs.save_changes_dialog import SaveChangesDialog
except ImportError:
    from ..views.dialogs.new_project_dialog import NewProjectDialog
    from ..views.dialogs.save_changes_dialog import SaveChangesDialog

from controllers.tracking_controller import TrackingController


class MainController(QObject):
    markers_changed = Signal()
    playback_time_changed = Signal(int)
    window_close_requested = Signal()

    def __init__(self):
        super().__init__()

        # ─── Models ───
        self.project = Project(name="Untitled")
        self.settings = AppSettings()

        # ─── Services ───
        self.video_service = VideoService()
        # CHANGED: используем singleton, чтобы main_window и контроллеры
        # разделяли один и тот же экземпляр (сигналы будут работать)
        self.history_manager = get_history_manager()
        self.project_io = ProjectIO()

        # ─── View ───
        self.main_window = MainWindow()

        # ─── Controllers ───
        self.playback_controller = PlaybackController(
            self.video_service,
            self.main_window.get_player_controls(),
            self.main_window
        )

        self.shortcut_controller = ShortcutController(self.main_window)
        self.filter_controller = FilterController()

        self._instance_edit_controller: Optional[InstanceEditController] = None
        self._settings_controller: Optional[SettingsController] = None
        self._custom_event_controller: Optional[CustomEventController] = None

        self.timeline_controller = TimelineController(
            self.project,
            None,
            self.main_window.get_segment_list_widget(),
            self.history_manager,
            self.settings,
            None
        )

        self.project_controller = ProjectController(self.project_io)
        self.project_controller.current_project = self.project

        self.export_controller: Optional[ExportController] = None
        self.autosave_manager = None

        self.markers = self.project.markers
        self.processor = self.video_service

        # ─── Wiring ───

        self._load_and_apply_settings()

        self.timeline_controller.set_playback_controller(self.playback_controller)
        self.timeline_controller.set_filter_controller(self.filter_controller)

        self.playback_controller.frame_changed.connect(
            lambda f: self.timeline_controller.seek_frame(f, update_playback=False)
        )

        self.timeline_controller.project_modified.connect(self.project_controller.mark_as_modified)

        self.main_window.set_timeline_controller(self.timeline_controller)
        self.timeline_controller.set_timeline_widget(self.main_window.get_timeline_widget())

        if hasattr(self.timeline_controller, "set_main_window"):
            self.timeline_controller.set_main_window(self)

        setattr(self.timeline_controller, "_main_controller", self)

        self.timeline_controller.set_custom_event_controller(self.get_custom_event_controller())

        self.main_window.set_controller(self)

        self._setup_connections()

        if hasattr(self.main_window, "window_closing"):
            self.main_window.window_closing.connect(self._on_window_closing)

        # CHANGED: передать callback авто-сохранения
        if hasattr(self.main_window, "set_autosave_callback"):
            self.main_window.set_autosave_callback(self.save_project_silent)

        if self.autosave_manager:
            self.autosave_manager.start()

        self._connect_progress_bar()

        self.tracking_controller = TrackingController(self)
        self.tracking_controller.set_overlay(self.main_window.tracking_overlay)
        self.tracking_controller.set_panel(self.main_window._tracking_panel)
        self.tracking_controller.connect_to_playback()

    # ─────────────────────────────────────────────────────────────────────────
    # Settings
    # ─────────────────────────────────────────────────────────────────────────

    def _load_and_apply_settings(self) -> None:
        settings_controller = self.get_settings_controller()
        if settings_controller.load_settings():
            self.settings = settings_controller.settings
            self.timeline_controller.settings = self.settings
            self._update_mode_indicator()
            print("Settings loaded and applied successfully")
        else:
            print("Failed to load settings, using defaults")

    def _update_mode_indicator(self) -> None:
        if hasattr(self.main_window, "update_mode_indicator"):
            self.main_window.update_mode_indicator(
                self.settings.recording_mode,
                self.settings.fixed_duration_sec,
                self.settings.pre_roll_sec,
                self.settings.post_roll_sec
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Connections
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_connections(self) -> None:
        self.main_window.open_video_triggered.connect(self._on_open_video)
        self.main_window.save_project_triggered.connect(self._on_save_project)
        self.main_window.load_project_triggered.connect(self._on_load_project)
        self.main_window.new_project_triggered.connect(self._on_new_project)
        self.main_window.open_settings_triggered.connect(self._on_open_settings)
        self.main_window.export_triggered.connect(self._on_export)
        self.main_window.open_preview_triggered.connect(self._on_open_preview)

        self.main_window.key_pressed.connect(self._on_key_pressed)
        self.shortcut_controller.shortcut_pressed.connect(self._on_shortcut_pressed)

        self.filter_controller.filters_changed.connect(self._on_filters_changed)

        self.main_window.video_dropped.connect(self._on_video_dropped)

        if hasattr(self.main_window, "event_shortcut_list_widget") and self.main_window.event_shortcut_list_widget is not None:
            self.main_window.event_shortcut_list_widget.event_selected.connect(self._on_event_btn_clicked)

        # Одиночные действия из segment_list
        segment_list = self.main_window.get_segment_list_widget()
        if segment_list is not None:
            segment_list.segment_jump_requested.connect(self._on_segment_jump)
            segment_list.segment_edit_requested.connect(self._on_segment_edit)
            segment_list.segment_delete_requested.connect(self._on_segment_delete)

            # Групповые действия
            if hasattr(segment_list, "batch_delete_requested"):
                segment_list.batch_delete_requested.connect(self._on_batch_delete)
            if hasattr(segment_list, "batch_change_type_requested"):
                segment_list.batch_change_type_requested.connect(self._on_batch_change_type)
            if hasattr(segment_list, "batch_export_requested"):
                segment_list.batch_export_requested.connect(self._on_batch_export)
            if hasattr(segment_list, "batch_duplicate_requested"):
                segment_list.batch_duplicate_requested.connect(self._on_batch_duplicate)

        
    def _connect_progress_bar(self) -> None:
        """Подключить VideoProgressBar к PlaybackController."""
        progress_bar = self.main_window.get_progress_bar()
        if not progress_bar:
            return

        # Позиция → прогресс-бар
        self.playback_controller.frame_changed.connect(progress_bar.set_current_frame)

        # Клик/drag на прогресс-баре → seek
        progress_bar.seek_requested.connect(self.playback_controller.seek_to_frame)

        # Пауза при drag, возобновление при отпускании
        self._was_playing_before_drag = False

        def on_drag_start():
            self._was_playing_before_drag = self.playback_controller.playing
            if self.playback_controller.playing:
                self.playback_controller.pause()
                self.main_window.get_player_controls().set_playing_state(False)

        def on_drag_end():
            if self._was_playing_before_drag:
                self.playback_controller.play()
                self.main_window.get_player_controls().set_playing_state(True)

        progress_bar.drag_started.connect(on_drag_start)
        progress_bar.drag_ended.connect(on_drag_end)

        # Пауза при drag, возобновление при отпускании
        self._was_playing_before_drag = False

        def on_drag_start():
            self._was_playing_before_drag = self.playback_controller.playing
            if self.playback_controller.playing:
                self.playback_controller.pause()
                self.player_controls.set_playing_state(False)

        def on_drag_end():
            if self._was_playing_before_drag:
                self.playback_controller.play()
                self.player_controls.set_playing_state(True)



    # ─────────────────────────────────────────────────────────────────────────
    # Window lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    def _on_window_closing(self, event) -> None:
        if self.project_controller.has_unsaved_changes():
            result = SaveChangesDialog.ask_save_changes(self.project.name, self.main_window)
            if result == SaveChangesDialog.CANCEL:
                event.ignore()
                return
            if result == SaveChangesDialog.SAVE:
                if not self.project_controller.save_project_auto(self.main_window):
                    event.ignore()
                    return

        if self.autosave_manager:
            self.autosave_manager.stop()

        if self._instance_edit_controller:
            self._instance_edit_controller.cleanup()
        if self._settings_controller:
            self._settings_controller.cleanup()
        if self._custom_event_controller:
            self._custom_event_controller.cleanup()

        event.accept()
        self.window_close_requested.emit()

    # ─────────────────────────────────────────────────────────────────────────
    # Filters
    # ─────────────────────────────────────────────────────────────────────────

    def _on_filters_changed(self) -> None:
        self.timeline_controller.refresh_view()

    # ─────────────────────────────────────────────────────────────────────────
    # Segment list actions — одиночные
    # ─────────────────────────────────────────────────────────────────────────

    def _on_segment_jump(self, marker_idx: int) -> None:
        markers = self.project.markers
        if 0 <= marker_idx < len(markers):
            marker = markers[marker_idx]
            self.playback_controller.seek_to_frame(marker.start_frame)

    def _on_segment_edit(self, marker_idx: int) -> None:
        self.open_segment_editor(marker_idx)

    def _on_segment_delete(self, marker_idx: int) -> None:
        self.delete_marker(marker_idx)
        # CHANGED: toast с кнопкой Undo
        if hasattr(self.main_window, "toast"):
            self.main_window.toast.warning(
                "Маркер удалён",
                action_text="Отмена",
                action_callback=lambda: self.timeline_controller.undo(),
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Segment list actions — ГРУППОВЫЕ
    # ─────────────────────────────────────────────────────────────────────────

    def _on_batch_delete(self, marker_indices: List[int]) -> None:
        if not marker_indices:
            return

        from PySide6.QtWidgets import QMessageBox
        count = len(marker_indices)
        reply = QMessageBox.question(
            self.main_window,
            "Удаление сегментов",
            f"Удалить {count} выделенных сегментов?\n\n"
            f"Это действие можно отменить (Ctrl+Z).",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.timeline_controller.batch_delete_markers(marker_indices)
            self.project_controller.mark_as_modified()
            # CHANGED: toast
            if hasattr(self.main_window, "toast"):
                self.main_window.toast.warning(
                    f"Удалено {count} маркеров",
                    action_text="Отмена",
                    action_callback=lambda: self.timeline_controller.undo(),
                )

    def _on_batch_change_type(self, marker_indices: List[int], new_event_name: str) -> None:
        if not marker_indices or not new_event_name:
            return
        self.timeline_controller.batch_change_event_type(marker_indices, new_event_name)
        self.project_controller.mark_as_modified()

    def _on_batch_export(self, marker_indices: List[int]) -> None:
        if not marker_indices:
            return
        video_path = getattr(self.project, "video_path", "")
        fps = self.video_service.get_fps() if self.video_service.cap else 30.0
        settings_ctrl = self.get_settings_controller()
        self.export_controller = ExportController(
            self.project, video_path, fps, settings_ctrl
        )
        preselected_ids = []
        for idx in marker_indices:
            if 0 <= idx < len(self.project.markers):
                preselected_ids.append(self.project.markers[idx].id)
        self.export_controller.show_dialog(preselected_ids=preselected_ids)

    def _on_batch_duplicate(self, marker_indices: List[int]) -> None:
        if not marker_indices:
            return
        self.timeline_controller.batch_duplicate_markers(marker_indices)
        self.project_controller.mark_as_modified()

    # ─────────────────────────────────────────────────────────────────────────
    # Segment editor
    # ─────────────────────────────────────────────────────────────────────────

    def open_segment_editor(self, marker_idx: int) -> None:
        if not (0 <= marker_idx < len(self.project.markers)):
            return
        controller = self.get_instance_edit_controller()
        if hasattr(controller, 'open_editor'):
            controller.open_editor(marker_idx)
        elif hasattr(controller, 'edit_marker'):
            controller.edit_marker(marker_idx)
        else:
            print(f"WARNING: InstanceEditController has no open_editor/edit_marker method")

    # ─────────────────────────────────────────────────────────────────────────
    # Playback speed
    # ─────────────────────────────────────────────────────────────────────────

    def set_playback_speed(self, speed: float) -> None:
        if hasattr(self.playback_controller, 'set_speed'):
            self.playback_controller.set_speed(speed)
        elif hasattr(self.playback_controller, 'speed'):
            self.playback_controller.speed = speed

    def get_video_width(self) -> int:
        if self.video_service and self.video_service.cap:
            import cv2
            return int(self.video_service.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        return 0

    def get_video_height(self) -> int:
        if self.video_service and self.video_service.cap:
            import cv2
            return int(self.video_service.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return 0

    # ─────────────────────────────────────────────────────────────────────────
    # Hotkeys
    # ─────────────────────────────────────────────────────────────────────────

    def _on_shortcut_pressed(self, key: str) -> None:
        if key == "PLAY_PAUSE":
            self.playback_controller.toggle_play_pause()
        elif key == "OPEN_VIDEO":
            self._on_open_video()
        elif key == "CANCEL":
            self.playback_controller.cancel_recording()
        elif key == "UNDO":
            # CHANGED: через timeline_controller для refresh_view
            self.timeline_controller.undo()
        elif key == "REDO":
            self.timeline_controller.redo()
        elif key == "SKIP_LEFT":
            self._on_skip_seconds(-5)
        elif key == "SKIP_RIGHT":
            self._on_skip_seconds(5)
        else:
            current_frame = self.playback_controller.current_frame
            fps = self.video_service.get_fps() if self.video_service.cap else 30.0
            self.timeline_controller.handle_hotkey(key, current_frame, fps)

    def _on_key_pressed(self, key: str) -> None:
        current_frame = self.playback_controller.current_frame
        fps = self.video_service.get_fps() if self.video_service.cap else 30.0
        self.timeline_controller.handle_hotkey(key, current_frame, fps)

    def _on_event_btn_clicked(self, event_name: str) -> None:
        current_frame = self.playback_controller.current_frame
        fps = self.video_service.get_fps() if self.video_service.cap else 30.0
        self.timeline_controller.handle_hotkey(event_name, current_frame, fps)

    # ─────────────────────────────────────────────────────────────────────────
    # Video
    # ─────────────────────────────────────────────────────────────────────────

    def _on_video_dropped(self, file_path: str) -> None:
        if file_path:
            self.load_video(file_path)

    def _on_skip_seconds(self, seconds: int) -> None:
        fps = self.video_service.get_fps() if self.video_service.cap else 30.0
        if fps <= 0:
            return
        frames_to_skip = int(seconds * fps)
        current_frame = self.playback_controller.current_frame
        new_frame = max(0, min(self.video_service.get_total_frames() - 1, current_frame + frames_to_skip))
        self.playback_controller.seek_to_frame(new_frame)

    def load_video(self, path: str) -> bool:
        success = self.playback_controller.load_video(path)
        if success:
            self.project.video_path = path
            total_frames = self.video_service.get_total_frames()
            fps = self.video_service.get_fps() if self.video_service.cap else 30.0

            self.main_window.get_timeline_widget().set_total_frames(total_frames)
            self.main_window.get_timeline_widget().set_fps(fps)

            self.timeline_controller.set_fps(fps)
            self.timeline_controller.init_tracks(total_frames)

            # ── Обновить progress bar ──                          # ← ДОБАВИТЬ
            progress_bar = self.main_window.get_progress_bar()     # ← ДОБАВИТЬ
            if progress_bar:                                       # ← ДОБАВИТЬ
                progress_bar.set_total_frames(total_frames)        # ← ДОБАВИТЬ
                progress_bar.set_fps(fps)

            self.main_window.set_window_title(path.split("/")[-1])

            # CHANGED: toast
            if hasattr(self.main_window, "show_toast_success"):
                self.main_window.show_toast_success(
                    f"Видео загружено: {path.split('/')[-1]}", duration_ms=2000
                )
        else:
            if hasattr(self.main_window, "show_toast_error"):
                self.main_window.show_toast_error("Не удалось загрузить видео")

        return success

    def _on_open_video(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Открыть видеофайл", "",
            "Видеофайлы (*.mp4 *.avi *.mov *.mkv *.wmv);;Все файлы (*)"
        )
        if file_path:
            self.load_video(file_path)
            self.project_controller.mark_as_modified()

    # ─────────────────────────────────────────────────────────────────────────
    # Project CRUD
    # ─────────────────────────────────────────────────────────────────────────

    def _on_save_project(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        success = False

        if getattr(self.project, "file_path", None):
            success = self.project_controller.save_project(self.project.file_path)
        else:
            file_path, _ = QFileDialog.getSaveFileName(
                self.main_window, "Сохранить проект", "project.hep",
                "Файлы проекта (*.hep);;Все файлы (*)"
            )
            if file_path:
                if not file_path.endswith(".hep"):
                    file_path += ".hep"
                success = self.project_controller.save_project(file_path)
                if success:
                    self.project.file_path = file_path

        # CHANGED: toast + mark_saved после сохранения
        if success:
            self.history_manager.mark_saved()
            if hasattr(self.main_window, "show_toast_success"):
                self.main_window.show_toast_success("Проект сохранён")
        elif hasattr(self.main_window, "show_toast_error"):
            self.main_window.show_toast_error("Не удалось сохранить проект")

    def _on_load_project(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Открыть проект", "",
            "Файлы проекта (*.hep);;Все файлы (*)"
        )
        if not file_path:
            return
        loaded_project = self.project_controller.load_project(file_path)
        if not loaded_project:
            if hasattr(self.main_window, "show_toast_error"):
                self.main_window.show_toast_error("Не удалось загрузить проект")
            return

        self.project = loaded_project
        self.project.file_path = file_path
        self.project_controller.current_project = self.project
        self.timeline_controller.project = self.project
        self.timeline_controller.refresh_view()

        # CHANGED: очистить историю при загрузке нового проекта
        self.history_manager.clear()

        if getattr(self.project, "video_path", None):
            self.load_video(self.project.video_path)
        self.main_window.set_window_title(f"{self.project.name} - {file_path.split('/')[-1]}")

        if hasattr(self.main_window, "show_toast_success"):
            self.main_window.show_toast_success("Проект загружен")

    def _on_new_project(self) -> None:
        if self.project_controller.has_unsaved_changes():
            result = SaveChangesDialog.ask_save_changes(self.project.name, self.main_window)
            if result == SaveChangesDialog.CANCEL:
                return
            if result == SaveChangesDialog.SAVE:
                if not self.project_controller.save_project_auto(self.main_window):
                    return
        mode = NewProjectDialog.get_new_project_mode(self.main_window)
        if mode is None:
            return
        if mode == NewProjectDialog.MODE_CURRENT_WINDOW:
            self._create_new_project_in_current_window()
        elif mode == NewProjectDialog.MODE_NEW_WINDOW:
            self._create_new_project_in_new_window()

    def _create_new_project_in_current_window(self) -> None:
        self.project = Project(name="Untitled")
        self.project_controller.current_project = self.project
        self.timeline_controller.project = self.project
        self.timeline_controller.refresh_view()
        self.playback_controller.pause()
        self.video_service.cleanup()
        self.playback_controller.current_frame = 0
        self.playback_controller.playing = False
        self.main_window.set_video_image(QPixmap())
        # ── Сбросить progress bar ──                             # ← ДОБАВИТЬ
        progress_bar = self.main_window.get_progress_bar()        # ← ДОБАВИТЬ
        if progress_bar:                                          # ← ДОБАВИТЬ
            progress_bar.set_total_frames(0)                      # ← ДОБАВИТЬ
            progress_bar.set_current_frame(0)
        self.main_window.set_window_title("Untitled")
        # CHANGED: clear() вместо clear_history()
        self.history_manager.clear()
        self.filter_controller.reset_all_filters()

    def _create_new_project_in_new_window(self) -> None:
        app_controller = get_application_controller()
        app_controller.create_new_window()

    # ─────────────────────────────────────────────────────────────────────────
    # Settings / export / preview
    # ─────────────────────────────────────────────────────────────────────────

    def _on_open_settings(self) -> None:
        settings_controller = self.get_settings_controller()
        custom_event_controller = self.get_custom_event_controller()
        dialog = SettingsDialog(settings_controller, custom_event_controller, self.main_window)
        dialog.accepted.connect(lambda: self._on_settings_saved(settings_controller.settings))
        dialog.exec()

    def _on_settings_saved(self, new_settings: AppSettings) -> None:
        self.settings = new_settings
        self.timeline_controller.settings = self.settings
        self.timeline_controller.refresh_view()
        self._update_mode_indicator()

    def _on_export(self) -> None:
        video_path = getattr(self.project, "video_path", "")
        fps = self.video_service.get_fps() if self.video_service.cap else 30.0
        settings_ctrl = self.get_settings_controller()
        self.export_controller = ExportController(
            self.project, video_path, fps, settings_ctrl
        )
        self.export_controller.show_dialog()

    def _on_open_preview(self) -> None:
        self.open_preview_window()

    def open_preview_window(self) -> None:
        from views.windows.preview_window import PreviewWindow
        preview_window = PreviewWindow(self, self.main_window)
        preview_window.show()

    # ─────────────────────────────────────────────────────────────────────────
    # Marker operations
    # ─────────────────────────────────────────────────────────────────────────

    def add_marker(self, start_frame: int, end_frame: int, event_name: str) -> None:
        self.timeline_controller.add_marker(start_frame, end_frame, event_name)
        self.project_controller.mark_as_modified()

    def delete_marker(self, marker_idx: int) -> None:
        self.timeline_controller.delete_marker(marker_idx)
        self.project_controller.mark_as_modified()

    def get_fps(self) -> float:
        return self.video_service.get_fps() if self.video_service.cap else 30.0

    def get_total_frames(self) -> int:
        return self.video_service.get_total_frames()

    def get_playback_speed(self) -> float:
        return self.playback_controller.get_speed()

    # ─────────────────────────────────────────────────────────────────────────
    # Controller factory
    # ─────────────────────────────────────────────────────────────────────────

    def get_instance_edit_controller(self) -> InstanceEditController:
        if self._instance_edit_controller is None:
            self._instance_edit_controller = InstanceEditController(self)
        return self._instance_edit_controller

    def get_settings_controller(self) -> SettingsController:
        if self._settings_controller is None:
            self._settings_controller = SettingsController()
            self._settings_controller.load_settings()
        return self._settings_controller

    def get_custom_event_controller(self) -> CustomEventController:
        if self._custom_event_controller is None:
            self._custom_event_controller = CustomEventController()
        return self._custom_event_controller

    # ─────────────────────────────────────────────────────────────────────────
    # Silent save (для auto-save)
    # ─────────────────────────────────────────────────────────────────────────

    def save_project_silent(self) -> bool:
        """Тихое сохранение для авто-сохранения (без диалогов).

        Возвращает:
            True  — если сохранение прошло успешно ИЛИ нечего сохранять
            False — если произошла ошибка при сохранении
        """
        try:
            file_path = getattr(self.project, "file_path", None)
            if not file_path:
                # Проект ещё ни разу не сохранён — это не ошибка,
                # просто пропускаем (нет куда сохранять)
                return True
            return self.project_controller.save_project(file_path)
        except Exception as e:
            print(f"Auto-save error: {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # App lifecycle
    # ─────────────────────────────────────────────────────────────────────────

    def run(self) -> None:
        self.main_window.show()

    def close(self) -> None:
        self.main_window.close()

    def cleanup(self) -> None:
        try:
            if hasattr(self.main_window, "window_closing"):
                self.main_window.window_closing.disconnect(self._on_window_closing)
        except Exception:
            pass