"""
Settings Controller - manages application settings.

Handles loading, saving, validation, and application of application settings
through a centralized interface for settings dialogs.
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from PySide6.QtCore import QObject, Signal

from models.config.app_settings import AppSettings
from services.serialization import SettingsManager


class SettingsController(QObject):
    """Controller for managing application settings."""

    settings_loaded = Signal(AppSettings)
    settings_saved = Signal()
    settings_changed = Signal(str, Any)        # (key, value) or ("*", AppSettings)
    validation_error = Signal(str, str)        # (field, message)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings: AppSettings = AppSettings()
        self.settings_manager = SettingsManager()

        # Snapshot for change tracking (dict is safest; no aliasing)
        self._original_settings_dict: Optional[Dict[str, Any]] = None

    # ─────────────────────────────────────────────────────────────────────────────
    # Load / Save / Change tracking
    # ─────────────────────────────────────────────────────────────────────────────

    def load_settings(self) -> bool:
        """Load settings from storage."""
        try:
            loaded_settings = self.settings_manager.load_settings()
            if loaded_settings:
                self.settings = loaded_settings
            else:
                self.settings = AppSettings()

            self._original_settings_dict = self.settings.to_dict()
            self.settings_loaded.emit(self.settings)
            return True

        except Exception as e:
            print(f"Error loading settings: {e}")
            return False

    def save_settings(self) -> bool:
        """Save current settings to storage."""
        try:
            success = self.settings_manager.save_settings(self.settings)
            if success:
                self._original_settings_dict = self.settings.to_dict()
                self.settings_saved.emit()
            return success

        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def reset_to_defaults(self) -> None:
        """Reset settings to application defaults (does not auto-save)."""
        self.settings = AppSettings()
        self.settings_changed.emit("*", self.settings)

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes."""
        if self._original_settings_dict is None:
            # not loaded yet => treat as changed
            return True
        return self.settings.to_dict() != self._original_settings_dict

    def apply_changes(self) -> bool:
        """Apply current settings (called when dialog is accepted)."""
        return self.save_settings()

    def discard_changes(self) -> None:
        """Discard current changes and revert to last loaded/saved snapshot."""
        if self._original_settings_dict is None:
            return
        try:
            self.settings = AppSettings.from_dict(self._original_settings_dict)
            self.settings_loaded.emit(self.settings)
        except Exception as e:
            print(f"Error discarding changes: {e}")

    # ─────────────────────────────────────────────────────────────────────────────
    # Recording settings
    # ─────────────────────────────────────────────────────────────────────────────

    def set_recording_mode(self, mode: str) -> None:
        if mode in ("dynamic", "fixed_length") and self.settings.recording_mode != mode:
            self.settings.recording_mode = mode
            self.settings_changed.emit("recording_mode", mode)

    def get_recording_mode(self) -> str:
        return self.settings.recording_mode

    def set_fixed_duration(self, seconds: int) -> None:
        if seconds <= 0:
            self.validation_error.emit("fixed_duration_sec", "Duration must be > 0")
            return
        if self.settings.fixed_duration_sec != seconds:
            self.settings.fixed_duration_sec = seconds
            self.settings_changed.emit("fixed_duration_sec", seconds)

    def get_fixed_duration(self) -> int:
        return self.settings.fixed_duration_sec

    def set_pre_roll(self, seconds: float) -> None:
        err = self.validate_duration(seconds, "Pre-roll")
        if err:
            self.validation_error.emit("pre_roll_sec", err)
            return
        if self.settings.pre_roll_sec != seconds:
            self.settings.pre_roll_sec = seconds
            self.settings_changed.emit("pre_roll_sec", seconds)

    def get_pre_roll(self) -> float:
        return self.settings.pre_roll_sec

    def set_post_roll(self, seconds: float) -> None:
        err = self.validate_duration(seconds, "Post-roll")
        if err:
            self.validation_error.emit("post_roll_sec", err)
            return
        if self.settings.post_roll_sec != seconds:
            self.settings.post_roll_sec = seconds
            self.settings_changed.emit("post_roll_sec", seconds)

    def get_post_roll(self) -> float:
        return self.settings.post_roll_sec

    # ─────────────────────────────────────────────────────────────────────────────
    # Hotkeys settings
    # ─────────────────────────────────────────────────────────────────────────────

    def set_hotkey(self, action: str, key: str) -> None:
        err = self.validate_hotkey(action, key)
        if err:
            self.validation_error.emit("hotkeys", err)
            return

        if self.settings.hotkeys.get(action) != key:
            self.settings.hotkeys[action] = key
            self.settings_changed.emit("hotkeys", self.settings.hotkeys.copy())

    def get_hotkey(self, action: str) -> str:
        return self.settings.hotkeys.get(action, "")

    def get_all_hotkeys(self) -> Dict[str, str]:
        return self.settings.hotkeys.copy()

    # ─────────────────────────────────────────────────────────────────────────────
    # Track color settings
    # ─────────────────────────────────────────────────────────────────────────────

    def set_track_color(self, track: str, color: str) -> None:
        # Optional: validate color format #RRGGBB if you want
        if self.settings.track_colors.get(track) != color:
            self.settings.track_colors[track] = color
            self.settings_changed.emit("track_colors", self.settings.track_colors.copy())

    def get_track_color(self, track: str) -> str:
        return self.settings.track_colors.get(track, "#000000")

    def get_all_track_colors(self) -> Dict[str, str]:
        return self.settings.track_colors.copy()

    # ─────────────────────────────────────────────────────────────────────────────
    # Window settings
    # ─────────────────────────────────────────────────────────────────────────────

    def set_window_geometry(self, x: int, y: int, width: int, height: int) -> None:
        err = self.validate_window_size(width, height)
        if err:
            self.validation_error.emit("window_geometry", err)
            return

        changed = (
            self.settings.window_x != x
            or self.settings.window_y != y
            or self.settings.window_width != width
            or self.settings.window_height != height
        )
        if changed:
            self.settings.window_x = x
            self.settings.window_y = y
            self.settings.window_width = width
            self.settings.window_height = height
            self.settings_changed.emit("window_geometry", (x, y, width, height))

    def get_window_geometry(self) -> tuple[int, int, int, int]:
        return (
            self.settings.window_x,
            self.settings.window_y,
            self.settings.window_width,
            self.settings.window_height,
        )

    # ─────────────────────────────────────────────────────────────────────────────
    # Autosave settings
    # ─────────────────────────────────────────────────────────────────────────────

    def set_autosave_enabled(self, enabled: bool) -> None:
        if self.settings.autosave_enabled != enabled:
            self.settings.autosave_enabled = enabled
            self.settings_changed.emit("autosave_enabled", enabled)

    def get_autosave_enabled(self) -> bool:
        return self.settings.autosave_enabled

    def set_autosave_interval(self, minutes: int) -> None:
        if minutes <= 0:
            self.validation_error.emit("autosave_interval_minutes", "Interval must be > 0")
            return
        if self.settings.autosave_interval_minutes != minutes:
            self.settings.autosave_interval_minutes = minutes
            self.settings_changed.emit("autosave_interval_minutes", minutes)

    def get_autosave_interval(self) -> int:
        return self.settings.autosave_interval_minutes

    # ─────────────────────────────────────────────────────────────────────────────
    # Language settings
    # ─────────────────────────────────────────────────────────────────────────────

    def set_language(self, language: str) -> None:
        if self.settings.language != language:
            self.settings.language = language
            self.settings_changed.emit("language", language)

    def get_language(self) -> str:
        return self.settings.language

    # ─────────────────────────────────────────────────────────────────────────────
    # Playback settings
    # ─────────────────────────────────────────────────────────────────────────────

    def set_playback_speed(self, speed: float) -> None:
        if speed <= 0:
            self.validation_error.emit("playback_speed", "Speed must be > 0")
            return
        if self.settings.playback_speed != speed:
            self.settings.playback_speed = speed
            self.settings_changed.emit("playback_speed", speed)

    def get_playback_speed(self) -> float:
        return self.settings.playback_speed

    # ─────────────────────────────────────────────────────────────────────────────
    # Recent projects
    # ─────────────────────────────────────────────────────────────────────────────

    def add_recent_project(self, path: str) -> None:
        if not path:
            return

        lst = list(self.settings.recent_projects)
        if path in lst:
            lst.remove(path)
        lst.insert(0, path)
        lst = lst[:10]

        if lst != self.settings.recent_projects:
            self.settings.recent_projects = lst
            self.settings_changed.emit("recent_projects", list(lst))

    def get_recent_projects(self) -> list[str]:
        return list(self.settings.recent_projects)

    def clear_recent_projects(self) -> None:
        if self.settings.recent_projects:
            self.settings.recent_projects.clear()
            self.settings_changed.emit("recent_projects", [])

    # ─────────────────────────────────────────────────────────────────────────────
    # Validation
    # ─────────────────────────────────────────────────────────────────────────────

    def validate_hotkey(self, action: str, key: str) -> Optional[str]:
        for other_action, other_key in self.settings.hotkeys.items():
            if other_action != action and other_key == key and key:
                return f"Hotkey '{key}' is already used for '{other_action}'"
        return None

    def validate_duration(self, value: float, field_name: str) -> Optional[str]:
        if value < 0:
            return f"{field_name} cannot be negative"
        if value > 300:
            return f"{field_name} cannot exceed 5 minutes"
        return None

    def validate_window_size(self, width: int, height: int) -> Optional[str]:
        if width < 800 or height < 600:
            return "Window size must be at least 800x600"
        if width > 4000 or height > 3000:
            return "Window size cannot exceed 4000x3000"
        return None

    # ─────────────────────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────────────────────

    def get_settings_dict(self) -> Dict[str, Any]:
        return self.settings.to_dict()

    def set_settings_dict(self, data: Dict[str, Any]) -> None:
        try:
            self.settings = AppSettings.from_dict(data)
            self.settings_changed.emit("*", self.settings)
        except Exception as e:
            print(f"Error setting settings from dict: {e}")

    def get_default_settings(self) -> AppSettings:
        return AppSettings()

    def export_settings(self, file_path: str) -> bool:
        try:
            return self.settings_manager.export_settings(self.settings, file_path)
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False

    def import_settings(self, file_path: str) -> bool:
        try:
            imported_settings = self.settings_manager.import_settings(file_path)
            if imported_settings:
                self.settings = imported_settings
                self.settings_changed.emit("*", self.settings)
                return True
            return False
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False

    def cleanup(self) -> None:
        """Cleanup resources (if needed)."""
        # If you add long-lived connections/timers later, disconnect/stop here.
        pass