from typing import Dict, List, Optional
from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QColor
from .custom_event_type import CustomEventType
from hockey_editor.utils.settings_manager import get_settings_manager


class CustomEventManager(QObject):
    """Manages user-defined event types with persistence."""

    # Сигнал об изменении событий - для обновления UI
    events_changed = Signal()

    # Default event types (always available)
    DEFAULT_EVENTS = [
        # Shooting
        CustomEventType(name='Goal', color='#FF0000', shortcut='G', description='Goal scored'),
        CustomEventType(name='Shot on Goal', color='#FF5722', shortcut='H', description='Shot on goal'),
        CustomEventType(name='Missed Shot', color='#FF9800', shortcut='M', description='Shot missed the net'),
        CustomEventType(name='Blocked Shot', color='#795548', shortcut='B', description='Shot blocked'),

        # Zone Entries/Exits
        CustomEventType(name='Zone Entry', color='#2196F3', shortcut='Z', description='Entry into offensive zone'),
        CustomEventType(name='Zone Exit', color='#03A9F4', shortcut='X', description='Exit from defensive zone'),
        CustomEventType(name='Dump In', color='#00BCD4', shortcut='D', description='Dump puck into zone'),

        # Possession
        CustomEventType(name='Turnover', color='#607D8B', shortcut='T', description='Loss of puck possession'),
        CustomEventType(name='Takeaway', color='#4CAF50', shortcut='A', description='Puck possession gained'),
        CustomEventType(name='Faceoff Win', color='#8BC34A', shortcut='F', description='Faceoff won'),
        CustomEventType(name='Faceoff Loss', color='#558B2F', shortcut='L', description='Faceoff lost'),

        # Defense
        CustomEventType(name='Defensive Block', color='#3F51B5', shortcut='K', description='Shot blocked in defense'),
        CustomEventType(name='Penalty', color='#9C27B0', shortcut='P', description='Penalty called'),
    ]

    def __init__(self):
        """Initialize manager and load settings."""
        super().__init__()  # Initialize QObject base class
        self.settings = get_settings_manager()
        self._custom_events: Dict[str, CustomEventType] = {}
        self._load_events()

    def _load_events(self) -> None:
        """Load custom events from settings."""
        events_data = self.settings.load_custom_events()
        self._custom_events = {}

        # Load from settings
        for event_dict in events_data:
            event = CustomEventType.from_dict(event_dict)
            self._custom_events[event.name] = event

        # Ensure defaults exist (in case not in settings)
        for default_event in self.DEFAULT_EVENTS:
            if default_event.name not in self._custom_events:
                self._custom_events[default_event.name] = default_event

    def get_all_events(self) -> List[CustomEventType]:
        """Get all event types (sorted by name)."""
        return sorted(self._custom_events.values(), key=lambda e: e.name)

    def get_event(self, name: str) -> Optional[CustomEventType]:
        """Get specific event type by name."""
        return self._custom_events.get(name)

    def add_event(self, event: CustomEventType) -> bool:
        """Add new custom event. Returns False if name already exists or shortcut conflicts."""
        if event.name in self._custom_events:
            return False

        # Validate color
        if not event.get_qcolor().isValid():
            return False

        # Validate exclusive shortcut
        if event.shortcut and not self._is_shortcut_available(event.shortcut, exclude_event=event.name):
            return False

        self._custom_events[event.name] = event
        self._save_events()
        return True

    def update_event(self, old_name: str, new_event: CustomEventType) -> bool:
        """Update existing event. Returns False if new name already exists (and differs from old) or shortcut conflicts."""
        if old_name not in self._custom_events:
            return False

        # Check if trying to rename to existing name
        if old_name != new_event.name and new_event.name in self._custom_events:
            return False

        # Validate color
        if not new_event.get_qcolor().isValid():
            return False

        # Validate exclusive shortcut
        if new_event.shortcut and not self._is_shortcut_available(new_event.shortcut, exclude_event=old_name):
            return False

        # Remove old entry if renaming
        if old_name != new_event.name:
            del self._custom_events[old_name]

        self._custom_events[new_event.name] = new_event
        self._save_events()
        return True

    def delete_event(self, name: str) -> bool:
        """Delete custom event. Cannot delete default events."""
        if name not in self._custom_events:
            return False

        # Protect default events
        default_names = {e.name for e in self.DEFAULT_EVENTS}
        if name in default_names:
            return False

        del self._custom_events[name]
        self._save_events()
        return True

    def reset_to_defaults(self) -> None:
        """Reset all events to defaults."""
        self._custom_events = {e.name: e for e in self.DEFAULT_EVENTS}
        self._save_events()

    def _save_events(self) -> None:
        """Save custom events to settings."""
        events_data = [event.to_dict() for event in self.get_all_events()]
        self.settings.save_custom_events(events_data)
        self.events_changed.emit()  # Уведомить UI об изменениях

    def _is_shortcut_available(self, shortcut: str, exclude_event: str = "") -> bool:
        """Check if a shortcut is available (not used by other events)."""
        if not shortcut:
            return True

        for event in self._custom_events.values():
            if event.name != exclude_event and event.shortcut.upper() == shortcut.upper():
                return False
        return True

    def get_event_by_hotkey(self, hotkey: str) -> Optional[CustomEventType]:
        """Get event by keyboard shortcut."""
        for event in self._custom_events.values():
            if event.shortcut.upper() == hotkey.upper():
                return event
        return None

    def get_event_color(self, name: str) -> QColor:
        """Get color for event type (or gray if not found)."""
        event = self.get_event(name)
        if event:
            return event.get_qcolor()
        return QColor('#CCCCCC')  # Gray fallback

    def get_event_hotkey(self, name: str) -> str:
        """Get keyboard shortcut for event type."""
        event = self.get_event(name)
        return event.shortcut if event else ""


# Global instance
_manager: Optional[CustomEventManager] = None


def get_custom_event_manager() -> CustomEventManager:
    """Get or create global CustomEventManager instance."""
    global _manager
    if _manager is None:
        _manager = CustomEventManager()
    return _manager


def reset_custom_event_manager() -> None:
    """Reset global manager (for testing)."""
    global _manager
    _manager = None
