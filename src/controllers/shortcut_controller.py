"""
Shortcut Controller - manages keyboard shortcuts and hotkeys for the application.

Handles global shortcuts, event shortcuts, and provides interface for
shortcut management and rebinding.
"""

from typing import Optional, Dict, Callable, Any
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QKeySequence, QShortcut

# Импорты для работы из корня проекта (main.py добавляет src в sys.path)
from utils.shortcut_manager import ShortcutManager
from services.events.custom_event_manager import get_custom_event_manager


class ShortcutController(QObject):
    """Controller for managing keyboard shortcuts and hotkeys."""

    # Signals
    shortcut_pressed = Signal(str)  # Emitted when a shortcut is pressed (key_name)
    shortcuts_updated = Signal()    # Emitted when shortcuts are updated

    def __init__(self, parent_window: Optional[QObject] = None) -> None:
        super().__init__(parent_window)

        self.parent_window = parent_window
        self.shortcut_manager = ShortcutManager(parent_window)
        self.event_manager = get_custom_event_manager()
        self.event_shortcuts: Dict[str, QShortcut] = {}

        # Connect to event manager changes
        self.event_manager.events_changed.connect(self._on_events_changed)

        # Setup initial shortcuts
        self._setup_shortcuts()

    def _setup_shortcuts(self) -> None:
        """Setup all shortcuts."""
        self._clear_event_shortcuts()
        self._setup_event_shortcuts()
        self._setup_global_shortcuts()

    def _clear_event_shortcuts(self) -> None:
        """Clear all event shortcuts."""
        for shortcut in self.event_shortcuts.values():
            if shortcut:
                shortcut.setParent(None)
        self.event_shortcuts.clear()

    def _setup_event_shortcuts(self) -> None:
        """Setup shortcuts for events (A, D, S and custom)."""
        for event in self.event_manager.get_all_events():
            if not event.shortcut:
                continue

            shortcut = QShortcut(QKeySequence(event.shortcut.upper()), self.parent_window)
            shortcut.activated.connect(
                lambda checked=False, key=event.shortcut.upper(): self._on_event_shortcut_activated(key)
            )
            self.event_shortcuts[event.name] = shortcut
            print(f"DEBUG: Setup event shortcut - {event.name}: {event.shortcut.upper()}")

    def _on_event_shortcut_activated(self, key: str):
        """Handle event shortcut activation with debug logging."""
        print(f"DEBUG: Event shortcut activated - key: {key}")
        self.shortcut_pressed.emit(key)

    def _setup_global_shortcuts(self) -> None:
        """Setup global application shortcuts."""
        # Playback shortcuts
        self.shortcut_manager.register_shortcut('PLAY_PAUSE', 'Space',
            lambda: self._on_global_shortcut_activated('PLAY_PAUSE'))
        self.shortcut_manager.register_shortcut('OPEN_VIDEO', 'Ctrl+O',
            lambda: self._on_global_shortcut_activated('OPEN_VIDEO'))
        self.shortcut_manager.register_shortcut('CANCEL', 'Escape',
            lambda: self._on_global_shortcut_activated('CANCEL'))

        # Menu shortcuts (handled by menu system)
        # SETTINGS, EXPORT, PREVIEW are handled through menu actions

        # Undo/Redo
        self.shortcut_manager.register_shortcut('UNDO', 'Ctrl+Z',
            lambda: self._on_global_shortcut_activated('UNDO'))
        self.shortcut_manager.register_shortcut('REDO', 'Ctrl+Shift+Z',
            lambda: self._on_global_shortcut_activated('REDO'))

        # Seek shortcuts
        self.shortcut_manager.register_shortcut('SKIP_LEFT', 'Left',
            lambda: self._on_global_shortcut_activated('SKIP_LEFT'))
        self.shortcut_manager.register_shortcut('SKIP_RIGHT', 'Right',
            lambda: self._on_global_shortcut_activated('SKIP_RIGHT'))

        print("DEBUG: Setup global shortcuts")

    def _on_global_shortcut_activated(self, key: str):
        """Handle global shortcut activation with debug logging."""
        print(f"DEBUG: Global shortcut activated - key: {key}")
        self.shortcut_pressed.emit(key)

    def _on_events_changed(self) -> None:
        """Handle event manager changes - rebind shortcuts."""
        self._setup_shortcuts()
        self.shortcuts_updated.emit()

    def rebind_shortcuts(self) -> None:
        """Rebind all shortcuts after settings changes."""
        self._setup_shortcuts()
        self.shortcuts_updated.emit()

    def get_shortcut_for_event(self, event_name: str) -> Optional[str]:
        """Get the shortcut for a specific event."""
        event = self.event_manager.get_event(event_name)
        return event.shortcut if event else None

    def set_shortcut_for_event(self, event_name: str, shortcut: str) -> bool:
        """Set a shortcut for an event.

        Args:
            event_name: Name of the event
            shortcut: New shortcut string

        Returns:
            True if successful, False otherwise
        """
        event = self.event_manager.get_event(event_name)
        if not event:
            return False

        event.shortcut = shortcut.upper()
        success = self.event_manager.update_event(event_name, event)

        if success:
            self._setup_shortcuts()  # Rebind shortcuts
            self.shortcuts_updated.emit()

        return success

    def is_shortcut_available(self, shortcut: str, exclude_event: Optional[str] = None) -> bool:
        """Check if a shortcut is available for use.

        Args:
            shortcut: Shortcut to check
            exclude_event: Event name to exclude from check

        Returns:
            True if shortcut is available
        """
        return self.event_manager._is_shortcut_available(shortcut.upper(), exclude_event)

    def get_all_shortcuts(self) -> Dict[str, str]:
        """Get all current shortcuts.

        Returns:
            Dictionary mapping event names to shortcuts
        """
        shortcuts = {}
        for event in self.event_manager.get_all_events():
            if event.shortcut:
                shortcuts[event.name] = event.shortcut
        return shortcuts
