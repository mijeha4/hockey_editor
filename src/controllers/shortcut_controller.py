from __future__ import annotations

import logging
from typing import Optional, Dict

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QKeySequence, QShortcut

from utils.shortcut_manager import ShortcutManager
from services.events.custom_event_manager import get_custom_event_manager

logger = logging.getLogger(__name__)


class ShortcutController(QObject):
    """Controller for managing keyboard shortcuts and hotkeys."""

    # Emitted when a shortcut is pressed (key_name). For event shortcuts: emits the shortcut key (e.g. "A").
    shortcut_pressed = Signal(str)
    shortcuts_updated = Signal()

    # Global shortcuts reserved by application (should not be used for event shortcuts)
    RESERVED_GLOBALS = {
        "SPACE", "CTRL+O", "ESCAPE", "CTRL+Z", "CTRL+SHIFT+Z", "LEFT", "RIGHT", "DELETE"
    }

    def __init__(self, parent_window: Optional[QObject] = None) -> None:
        super().__init__(parent_window)

        self.parent_window = parent_window
        self.shortcut_manager = ShortcutManager(parent_window)
        self.event_manager = get_custom_event_manager()

        self.event_shortcuts: Dict[str, QShortcut] = {}

        self.event_manager.events_changed.connect(self._on_events_changed)
        self._setup_shortcuts()

    # ─── Setup ────────────────────────────────────────────────────────────────

    def _setup_shortcuts(self) -> None:
        self._clear_event_shortcuts()
        self._clear_global_shortcuts()
        self._setup_event_shortcuts()
        self._setup_global_shortcuts()

    def _clear_event_shortcuts(self) -> None:
        for shortcut in self.event_shortcuts.values():
            if shortcut:
                shortcut.setEnabled(False)
                shortcut.setParent(None)
                shortcut.deleteLater()
        self.event_shortcuts.clear()

    def _clear_global_shortcuts(self) -> None:
        # depends on ShortcutManager implementation, but typical pattern:
        for name in list(getattr(self.shortcut_manager, "shortcuts", {}).keys()):
            self.shortcut_manager.unregister_shortcut(name)

    def _setup_event_shortcuts(self) -> None:
        all_events = self.event_manager.get_all_events()
        logger.debug("Setting up event shortcuts. Events count=%d", len(all_events))

        for event in all_events:
            if not event.shortcut:
                continue

            event_name = event.name
            key_seq = event.shortcut.upper()

            # Optional: prevent conflict with reserved globals
            if key_seq.upper() in self.RESERVED_GLOBALS:
                logger.warning("Event '%s' uses reserved global shortcut '%s' - skipped", event_name, key_seq)
                continue

            sc = QShortcut(QKeySequence(key_seq), self.parent_window)
            # If you need application-wide shortcuts, you can change context:
            # sc.setContext(Qt.ApplicationShortcut)
            sc.setContext(Qt.WidgetWithChildrenShortcut)

            sc.activated.connect(
                lambda name=event_name, key=key_seq: self._on_event_shortcut_activated(name, key)
            )

            self.event_shortcuts[event_name] = sc
            logger.debug("Bound event shortcut: %s -> %s", event_name, key_seq)

    def _setup_global_shortcuts(self) -> None:
        # Playback
        self.shortcut_manager.register_shortcut("PLAY_PAUSE", "Space",
            lambda: self._on_global_shortcut_activated("PLAY_PAUSE"))
        self.shortcut_manager.register_shortcut("OPEN_VIDEO", "Ctrl+O",
            lambda: self._on_global_shortcut_activated("OPEN_VIDEO"))
        self.shortcut_manager.register_shortcut("CANCEL", "Escape",
            lambda: self._on_global_shortcut_activated("CANCEL"))

        # Undo/Redo
        self.shortcut_manager.register_shortcut("UNDO", "Ctrl+Z",
            lambda: self._on_global_shortcut_activated("UNDO"))
        self.shortcut_manager.register_shortcut("REDO", "Ctrl+Shift+Z",
            lambda: self._on_global_shortcut_activated("REDO"))

        # Seek
        self.shortcut_manager.register_shortcut("SKIP_LEFT", "Left",
            lambda: self._on_global_shortcut_activated("SKIP_LEFT"))
        self.shortcut_manager.register_shortcut("SKIP_RIGHT", "Right",
            lambda: self._on_global_shortcut_activated("SKIP_RIGHT"))

        # Delete
        self.shortcut_manager.register_shortcut("DELETE", "Delete",
            lambda: self._on_global_shortcut_activated("DELETE"))

        logger.debug("Global shortcuts set up")

    # ─── Handlers ──────────────────────────────────────────────────────────────

    def _on_event_shortcut_activated(self, event_name: str, key: str) -> None:
        logger.debug("Event shortcut activated: event=%s key=%s", event_name, key)
        # сохраняем текущее поведение: наружу отдаём key, а не event_name
        self.shortcut_pressed.emit(key)

    def _on_global_shortcut_activated(self, key: str) -> None:
        logger.debug("Global shortcut activated: key=%s", key)
        self.shortcut_pressed.emit(key)

    def _on_events_changed(self) -> None:
        logger.debug("Events changed -> rebind shortcuts")
        self._setup_shortcuts()
        self.shortcuts_updated.emit()

    def rebind_shortcuts(self) -> None:
        logger.debug("Rebind shortcuts called")
        self._setup_shortcuts()
        self.shortcuts_updated.emit()

    # ─── Public API ────────────────────────────────────────────────────────────

    def cleanup_all_shortcuts(self) -> None:
        self._clear_event_shortcuts()
        self._clear_global_shortcuts()

    def get_shortcut_for_event(self, event_name: str) -> Optional[str]:
        event = self.event_manager.get_event(event_name)
        return event.shortcut if event else None

    def set_shortcut_for_event(self, event_name: str, shortcut: str) -> bool:
        event = self.event_manager.get_event(event_name)
        if not event:
            return False

        shortcut = (shortcut or "").upper()

        # Optional: check reserved global conflicts
        if shortcut and shortcut in self.RESERVED_GLOBALS:
            return False

        event.shortcut = shortcut
        success = self.event_manager.update_event(event_name, event)
        if success:
            self._setup_shortcuts()
            self.shortcuts_updated.emit()
        return success

    def is_shortcut_available(self, shortcut: str, exclude_event: Optional[str] = None) -> bool:
        shortcut = (shortcut or "").upper()

        if shortcut in self.RESERVED_GLOBALS:
            return False

        # Prefer public API if exists
        if hasattr(self.event_manager, "is_shortcut_available"):
            return self.event_manager.is_shortcut_available(shortcut, exclude_event)

        # Fallback to old private method (not recommended)
        return self.event_manager._is_shortcut_available(shortcut, exclude_event)

    def get_all_shortcuts(self) -> Dict[str, str]:
        shortcuts: Dict[str, str] = {}
        for event in self.event_manager.get_all_events():
            if event.shortcut:
                shortcuts[event.name] = event.shortcut
        return shortcuts