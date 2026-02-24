from __future__ import annotations

from typing import Dict, List, Optional, Set

from PySide6.QtCore import Signal, QObject
from PySide6.QtGui import QColor

from services.serialization.settings_manager import get_settings_manager
from .custom_event_type import CustomEventType


class CustomEventManager(QObject):
    """Manages event types with persistence for custom events."""
    events_changed = Signal()

    DEFAULT_EVENTS: List[CustomEventType] = [
        CustomEventType(name="Goal", color="#FF0000", shortcut="G", description="Goal scored"),
        CustomEventType(name="Shot on Goal", color="#FF5722", shortcut="H", description="Shot on goal"),
        CustomEventType(name="Missed Shot", color="#FF9800", shortcut="M", description="Shot missed the net"),
        CustomEventType(name="Blocked Shot", color="#795548", shortcut="B", description="Shot blocked"),

        CustomEventType(name="Zone Entry", color="#2196F3", shortcut="Z", description="Entry into offensive zone"),
        CustomEventType(name="Zone Exit", color="#03A9F4", shortcut="X", description="Exit from defensive zone"),
        CustomEventType(name="Dump In", color="#00BCD4", shortcut="D", description="Dump puck into zone"),

        CustomEventType(name="Turnover", color="#607D8B", shortcut="T", description="Loss of puck possession"),
        CustomEventType(name="Takeaway", color="#4CAF50", shortcut="A", description="Puck possession gained"),
        CustomEventType(name="Faceoff Win", color="#8BC34A", shortcut="F", description="Faceoff won"),
        CustomEventType(name="Faceoff Loss", color="#558B2F", shortcut="L", description="Faceoff lost"),

        CustomEventType(name="Defensive Block", color="#3F51B5", shortcut="K", description="Shot blocked in defense"),
        CustomEventType(name="Penalty", color="#9C27B0", shortcut="P", description="Penalty called"),
    ]

    def __init__(self):
        super().__init__()
        self.settings = get_settings_manager()
        self._custom_events: Dict[str, CustomEventType] = {}

        # FIX: Overrides for default events (shortcut rebinding etc.)
        # Stored separately so defaults are never lost, but can be customized
        self._default_overrides: Dict[str, CustomEventType] = {}

        self._load_custom_events()

    @property
    def _default_names(self) -> Set[str]:
        return {e.name for e in self.DEFAULT_EVENTS}

    def is_default_event(self, name: str) -> bool:
        return name in self._default_names

    def get_default_events(self) -> List[CustomEventType]:
        return list(self.DEFAULT_EVENTS)

    def _load_custom_events(self) -> None:
        data = self.settings.load_custom_events() or []
        custom: Dict[str, CustomEventType] = {}
        overrides: Dict[str, CustomEventType] = {}

        for d in data:
            ev = CustomEventType.from_dict(d)
            if not ev.name:
                continue
            if not ev.get_qcolor().isValid():
                continue

            if ev.name in self._default_names:
                # FIX: This is an override for a default event (e.g. rebound shortcut)
                overrides[ev.name] = ev
            else:
                custom[ev.name] = ev

        self._custom_events = custom
        self._default_overrides = overrides

    def _save_custom_events(self) -> None:
        # FIX: Save both custom events AND default overrides
        all_to_save = list(self.get_custom_events()) + list(self._default_overrides.values())
        data = [e.to_dict() for e in all_to_save]
        self.settings.save_custom_events(data)

    def get_custom_events(self) -> List[CustomEventType]:
        return sorted(self._custom_events.values(), key=lambda e: e.name)

    def get_all_events(self) -> List[CustomEventType]:
        merged: Dict[str, CustomEventType] = {e.name: e for e in self.DEFAULT_EVENTS}
        # Apply overrides for default events
        merged.update(self._default_overrides)
        merged.update(self._custom_events)

        # ── Plugin integration: добавить события из плагинов ──
        try:
            from plugins.registry import get_plugin_registry
            registry = get_plugin_registry()
            for plugin in registry.get_event_plugins():
                for event_data in plugin.get_event_types():
                    name = event_data.get("name", "")
                    if name and name not in merged:
                        merged[name] = CustomEventType(
                            name=name,
                            color=event_data.get("color", "#CCCCCC"),
                            shortcut=event_data.get("shortcut", ""),
                            description=event_data.get("description", ""),
                        )
        except ImportError:
            pass  # Plugin system not available
        except Exception as e:
            print(f"Plugin event integration error: {e}")

        return sorted(merged.values(), key=lambda e: e.name)

    def get_event(self, name: str) -> Optional[CustomEventType]:
        if name in self._custom_events:
            return self._custom_events[name]
        # FIX: Check overrides before raw defaults
        if name in self._default_overrides:
            return self._default_overrides[name]
        for e in self.DEFAULT_EVENTS:
            if e.name == name:
                return e
        return None

    def is_shortcut_available(self, shortcut: str, exclude_event: str = "") -> bool:
        sc = (shortcut or "").upper().strip()
        if not sc:
            return True
        for ev in self.get_all_events():
            if ev.name != exclude_event and (ev.shortcut or "").upper() == sc:
                return False
        return True

    def _is_shortcut_available(self, shortcut: str, exclude_event: str = "") -> bool:
        return self.is_shortcut_available(shortcut, exclude_event)

    def add_event(self, event: CustomEventType) -> bool:
        if not event.name or event.name in self._default_names or event.name in self._custom_events:
            return False
        if not event.get_qcolor().isValid():
            return False
        if event.shortcut and not self.is_shortcut_available(event.shortcut, exclude_event=event.name):
            return False

        self._custom_events[event.name] = event
        self._save_custom_events()
        self.events_changed.emit()
        return True

    def update_event(self, old_name: str, new_event: CustomEventType) -> bool:
        """Update an event (custom or default).

        For default events: stores an override (original default is preserved).
        For custom events: replaces the event, optionally renaming.
        """
        if not old_name or not new_event.name:
            return False

        if not new_event.get_qcolor().isValid():
            return False

        if new_event.shortcut and not self.is_shortcut_available(
            new_event.shortcut, exclude_event=old_name
        ):
            return False

        # ─── Case 1: Default event override ───
        if old_name in self._default_names:
            # Default events cannot be renamed
            if new_event.name != old_name:
                return False

            self._default_overrides[old_name] = new_event
            self._save_custom_events()
            self.events_changed.emit()
            return True

        # ─── Case 2: Custom event update ───
        if old_name not in self._custom_events:
            return False

        # Rename check
        if new_event.name != old_name:
            if new_event.name in self._default_names or new_event.name in self._custom_events:
                return False
            del self._custom_events[old_name]

        self._custom_events[new_event.name] = new_event
        self._save_custom_events()
        self.events_changed.emit()
        return True

    def delete_event(self, name: str) -> bool:
        # FIX: Allow removing overrides (restores default)
        if name in self._default_overrides:
            del self._default_overrides[name]
            self._save_custom_events()
            self.events_changed.emit()
            return True

        if name not in self._custom_events:
            return False
        del self._custom_events[name]
        self._save_custom_events()
        self.events_changed.emit()
        return True

    def reset_to_defaults(self) -> None:
        if not self._custom_events and not self._default_overrides:
            return
        self._custom_events.clear()
        self._default_overrides.clear()
        self._save_custom_events()
        self.events_changed.emit()

    def get_event_by_hotkey(self, hotkey: str) -> Optional[CustomEventType]:
        hk = (hotkey or "").upper()
        for ev in self.get_all_events():
            if (ev.shortcut or "").upper() == hk:
                return ev
        return None

    def get_event_color(self, name: str) -> QColor:
        ev = self.get_event(name)
        return ev.get_qcolor() if ev else QColor("#CCCCCC")

    def get_event_hotkey(self, name: str) -> str:
        ev = self.get_event(name)
        return ev.shortcut if ev else ""


_manager: Optional[CustomEventManager] = None


def get_custom_event_manager() -> CustomEventManager:
    global _manager
    if _manager is None:
        _manager = CustomEventManager()
    return _manager