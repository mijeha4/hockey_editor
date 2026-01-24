"""
Settings Controller - manages application settings.

Handles loading, saving, validation, and application of application settings
through a centralized interface for settings dialogs.
"""

from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

# Импорты для работы из корня проекта (main.py добавляет src в sys.path)
from models.config.app_settings import AppSettings
from services.serialization import SettingsManager


class SettingsController(QObject):
    """Controller for managing application settings."""

    # Signals
    settings_loaded = Signal(AppSettings)      # Settings loaded successfully
    settings_saved = Signal()                  # Settings saved successfully
    settings_changed = Signal(str, Any)        # Individual setting changed (key, value)
    validation_error = Signal(str, str)        # Validation error (field, message)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = AppSettings()
        self.settings_manager = SettingsManager()
        self.original_settings = None  # For change tracking

    def load_settings(self) -> bool:
        """Load settings from storage."""
        try:
            loaded_settings = self.settings_manager.load_settings()
            if loaded_settings:
                self.settings = loaded_settings
                self.original_settings = loaded_settings
                self.settings_loaded.emit(self.settings)
                return True
            else:
                # Use defaults
                self.original_settings = AppSettings()
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
                self.original_settings = self.settings
                self.settings_saved.emit()
            return success
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def reset_to_defaults(self):
        """Reset settings to application defaults."""
        self.settings = AppSettings()
        self.settings_changed.emit("*", self.settings)  # Signal all settings changed

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes."""
        if self.original_settings is None:
            return True
        return self.settings.to_dict() != self.original_settings.to_dict()

    def apply_changes(self):
        """Apply current settings (called when dialog is accepted)."""
        # Here we could notify other parts of the application about settings changes
        # For now, just save
        self.save_settings()

    def discard_changes(self):
        """Discard current changes and revert to original settings."""
        if self.original_settings:
            self.settings = self.original_settings
            self.settings_loaded.emit(self.settings)

    # Recording settings
    def set_recording_mode(self, mode: str):
        """Set recording mode."""
        if mode in ['dynamic', 'fixed_length']:
            self.settings.recording_mode = mode
            self.settings_changed.emit('recording_mode', mode)

    def get_recording_mode(self) -> str:
        """Get current recording mode."""
        return self.settings.recording_mode

    def set_fixed_duration(self, seconds: int):
        """Set fixed duration for fixed_length mode."""
        if seconds > 0:
            self.settings.fixed_duration_sec = seconds
            self.settings_changed.emit('fixed_duration_sec', seconds)

    def get_fixed_duration(self) -> int:
        """Get fixed duration."""
        return self.settings.fixed_duration_sec

    def set_pre_roll(self, seconds: float):
        """Set pre-roll duration."""
        if seconds >= 0:
            self.settings.pre_roll_sec = seconds
            self.settings_changed.emit('pre_roll_sec', seconds)

    def get_pre_roll(self) -> float:
        """Get pre-roll duration."""
        return self.settings.pre_roll_sec

    def set_post_roll(self, seconds: float):
        """Set post-roll duration."""
        if seconds >= 0:
            self.settings.post_roll_sec = seconds
            self.settings_changed.emit('post_roll_sec', seconds)

    def get_post_roll(self) -> float:
        """Get post-roll duration."""
        return self.settings.post_roll_sec

    # Hotkey settings
    def set_hotkey(self, action: str, key: str):
        """Set hotkey for action."""
        self.settings.hotkeys[action] = key
        self.settings_changed.emit('hotkeys', self.settings.hotkeys)

    def get_hotkey(self, action: str) -> str:
        """Get hotkey for action."""
        return self.settings.hotkeys.get(action, "")

    def get_all_hotkeys(self) -> Dict[str, str]:
        """Get all hotkeys."""
        return self.settings.hotkeys.copy()

    # Track color settings
    def set_track_color(self, track: str, color: str):
        """Set color for track."""
        self.settings.track_colors[track] = color
        self.settings_changed.emit('track_colors', self.settings.track_colors)

    def get_track_color(self, track: str) -> str:
        """Get color for track."""
        return self.settings.track_colors.get(track, "#000000")

    def get_all_track_colors(self) -> Dict[str, str]:
        """Get all track colors."""
        return self.settings.track_colors.copy()

    # Window settings
    def set_window_geometry(self, x: int, y: int, width: int, height: int):
        """Set window geometry."""
        self.settings.window_x = x
        self.settings.window_y = y
        self.settings.window_width = width
        self.settings.window_height = height
        self.settings_changed.emit('window_geometry', (x, y, width, height))

    def get_window_geometry(self) -> tuple[int, int, int, int]:
        """Get window geometry."""
        return (
            self.settings.window_x,
            self.settings.window_y,
            self.settings.window_width,
            self.settings.window_height
        )

    # Autosave settings
    def set_autosave_enabled(self, enabled: bool):
        """Enable/disable autosave."""
        self.settings.autosave_enabled = enabled
        self.settings_changed.emit('autosave_enabled', enabled)

    def get_autosave_enabled(self) -> bool:
        """Get autosave enabled state."""
        return self.settings.autosave_enabled

    def set_autosave_interval(self, minutes: int):
        """Set autosave interval in minutes."""
        if minutes > 0:
            self.settings.autosave_interval_minutes = minutes
            self.settings_changed.emit('autosave_interval_minutes', minutes)

    def get_autosave_interval(self) -> int:
        """Get autosave interval."""
        return self.settings.autosave_interval_minutes

    # Language settings
    def set_language(self, language: str):
        """Set application language."""
        self.settings.language = language
        self.settings_changed.emit('language', language)

    def get_language(self) -> str:
        """Get current language."""
        return self.settings.language

    # Playback settings
    def set_playback_speed(self, speed: float):
        """Set default playback speed."""
        if speed > 0:
            self.settings.playback_speed = speed
            self.settings_changed.emit('playback_speed', speed)

    def get_playback_speed(self) -> float:
        """Get default playback speed."""
        return self.settings.playback_speed

    # Recent projects
    def add_recent_project(self, path: str):
        """Add project to recent projects list."""
        if path in self.settings.recent_projects:
            self.settings.recent_projects.remove(path)

        self.settings.recent_projects.insert(0, path)

        # Keep only last 10 projects
        self.settings.recent_projects = self.settings.recent_projects[:10]

        self.settings_changed.emit('recent_projects', self.settings.recent_projects)

    def get_recent_projects(self) -> list[str]:
        """Get recent projects list."""
        return self.settings.recent_projects.copy()

    def clear_recent_projects(self):
        """Clear recent projects list."""
        self.settings.recent_projects.clear()
        self.settings_changed.emit('recent_projects', [])

    # Validation methods
    def validate_hotkey(self, action: str, key: str) -> Optional[str]:
        """Validate hotkey assignment."""
        # Check for conflicts with other hotkeys
        for other_action, other_key in self.settings.hotkeys.items():
            if other_action != action and other_key == key:
                return f"Hotkey '{key}' is already used for '{other_action}'"
        return None

    def validate_duration(self, value: float, field_name: str) -> Optional[str]:
        """Validate duration value."""
        if value < 0:
            return f"{field_name} cannot be negative"
        if value > 300:  # 5 minutes max
            return f"{field_name} cannot exceed 5 minutes"
        return None

    def validate_window_size(self, width: int, height: int) -> Optional[str]:
        """Validate window dimensions."""
        if width < 800 or height < 600:
            return "Window size must be at least 800x600"
        if width > 4000 or height > 3000:
            return "Window size cannot exceed 4000x3000"
        return None

    # Utility methods
    def get_settings_dict(self) -> Dict[str, Any]:
        """Get settings as dictionary."""
        return self.settings.to_dict()

    def set_settings_dict(self, data: Dict[str, Any]):
        """Set settings from dictionary."""
        try:
            self.settings = AppSettings.from_dict(data)
            self.settings_changed.emit("*", self.settings)
        except Exception as e:
            print(f"Error setting settings from dict: {e}")

    def get_default_settings(self) -> AppSettings:
        """Get default settings instance."""
        return AppSettings()

    def export_settings(self, file_path: str) -> bool:
        """Export settings to file."""
        try:
            return self.settings_manager.export_settings(self.settings, file_path)
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False

    def import_settings(self, file_path: str) -> bool:
        """Import settings from file."""
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

    def cleanup(self):
        """Cleanup resources."""
        # Disconnect signals if needed
        pass
