"""
Custom Event Controller - manages custom event types.

Handles CRUD operations for custom event types, including validation,
import/export, and synchronization with the event manager service.
"""

from typing import List, Optional, Dict, Any
from PySide6.QtCore import QObject, Signal

# Импорты для работы из корня проекта (main.py добавляет src в sys.path)
from services.events.custom_event_manager import get_custom_event_manager, CustomEventManager
from services.events.custom_event_type import CustomEventType


class CustomEventController(QObject):
    """Controller for managing custom event types."""

    # Signals
    events_changed = Signal()                  # Event list changed
    event_added = Signal(CustomEventType)      # New event added
    event_updated = Signal(str, CustomEventType)  # Event updated (old_name, new_event)
    event_deleted = Signal(str)                # Event deleted (name)
    events_reset = Signal()                    # Events reset to defaults
    validation_error = Signal(str, str)        # Validation error (field, message)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.event_manager: CustomEventManager = get_custom_event_manager()

        # Connect to manager signals
        self.event_manager.events_changed.connect(self.events_changed)

    def get_all_events(self) -> List[CustomEventType]:
        """Get all event types."""
        return self.event_manager.get_all_events()

    def get_event(self, name: str) -> Optional[CustomEventType]:
        """Get event by name."""
        return self.event_manager.get_event(name)

    def add_event(self, event: CustomEventType) -> bool:
        """Add new event type."""
        # Validate event
        validation_result = self._validate_event(event)
        if validation_result:
            self.validation_error.emit("general", validation_result)
            return False

        # Check for conflicts
        if self.event_manager.get_event(event.name):
            self.validation_error.emit("name", f"Event '{event.name}' already exists")
            return False

        # Check hotkey conflicts
        if event.shortcut:
            conflict = self._check_hotkey_conflict(event.name, event.shortcut)
            if conflict:
                self.validation_error.emit("shortcut", f"Shortcut '{event.shortcut}' is already used by '{conflict}'")
                return False

        # Add event
        success = self.event_manager.add_event(event)
        if success:
            self.event_added.emit(event)

        return success

    def update_event(self, old_name: str, new_event: CustomEventType) -> bool:
        """Update existing event type."""
        # Validate event
        validation_result = self._validate_event(new_event)
        if validation_result:
            self.validation_error.emit("general", validation_result)
            return False

        # Check name conflicts (if name changed)
        if old_name != new_event.name and self.event_manager.get_event(new_event.name):
            self.validation_error.emit("name", f"Event '{new_event.name}' already exists")
            return False

        # Check hotkey conflicts
        if new_event.shortcut:
            conflict = self._check_hotkey_conflict(new_event.name, new_event.shortcut)
            if conflict:
                self.validation_error.emit("shortcut", f"Shortcut '{new_event.shortcut}' is already used by '{conflict}'")
                return False

        # Update event
        success = self.event_manager.update_event(old_name, new_event)
        if success:
            self.event_updated.emit(old_name, new_event)

        return success

    def delete_event(self, name: str) -> bool:
        """Delete event type."""
        # Check if it's a default event
        event = self.event_manager.get_event(name)
        if not event:
            self.validation_error.emit("general", f"Event '{name}' not found")
            return False

        # Check if it's a default event
        if name in {e.name for e in self.event_manager.DEFAULT_EVENTS}:
            self.validation_error.emit("general", f"Cannot delete default event '{name}'")
            return False

        # Delete event
        success = self.event_manager.delete_event(name)
        if success:
            self.event_deleted.emit(name)

        return success

    def reset_to_defaults(self):
        """Reset events to application defaults."""
        self.event_manager.reset_to_defaults()
        self.events_reset.emit()

    def export_events(self, file_path: str) -> bool:
        """Export events to file."""
        try:
            return self.event_manager.export_events(file_path)
        except Exception as e:
            self.validation_error.emit("export", f"Export failed: {str(e)}")
            return False

    def import_events(self, file_path: str) -> bool:
        """Import events from file."""
        try:
            success = self.event_manager.import_events(file_path)
            if success:
                self.events_changed.emit()
            return success
        except Exception as e:
            self.validation_error.emit("import", f"Import failed: {str(e)}")
            return False

    def get_default_events(self) -> List[CustomEventType]:
        """Get default event types."""
        return self.event_manager.DEFAULT_EVENTS.copy()

    def is_default_event(self, name: str) -> bool:
        """Check if event is a default event."""
        return name in {e.name for e in self.event_manager.DEFAULT_EVENTS}

    def get_events_by_category(self) -> Dict[str, List[CustomEventType]]:
        """Get events grouped by category (shooting, possession, etc.)."""
        categories = {
            "Shooting": [],
            "Zone Transitions": [],
            "Possession": [],
            "Defense": [],
            "Other": []
        }

        # Categorize events based on their characteristics
        for event in self.get_all_events():
            name_lower = event.name.lower()
            desc_lower = event.description.lower()

            if any(word in name_lower or word in desc_lower
                   for word in ['goal', 'shot', 'missed', 'blocked']):
                categories["Shooting"].append(event)
            elif any(word in name_lower or word in desc_lower
                    for word in ['zone', 'dump', 'entry', 'exit']):
                categories["Zone Transitions"].append(event)
            elif any(word in name_lower or word in desc_lower
                    for word in ['turnover', 'takeaway', 'faceoff', 'possession']):
                categories["Possession"].append(event)
            elif any(word in name_lower or word in desc_lower
                    for word in ['defensive', 'block', 'penalty']):
                categories["Defense"].append(event)
            else:
                categories["Other"].append(event)

        # Remove empty categories
        return {k: v for k, v in categories.items() if v}

    def get_event_stats(self) -> Dict[str, Any]:
        """Get statistics about events."""
        events = self.get_all_events()
        default_count = len([e for e in events if self.is_default_event(e.name)])
        custom_count = len(events) - default_count

        return {
            "total_events": len(events),
            "default_events": default_count,
            "custom_events": custom_count,
            "events_with_shortcuts": len([e for e in events if e.shortcut]),
            "events_with_descriptions": len([e for e in events if e.description])
        }

    def validate_event_data(self, name: str, color: str, shortcut: str = "",
                           description: str = "") -> List[str]:
        """Validate event data and return list of error messages."""
        errors = []

        # Validate name
        if not name.strip():
            errors.append("Event name cannot be empty")
        elif len(name.strip()) > 50:
            errors.append("Event name cannot exceed 50 characters")

        # Validate color
        if not color.startswith('#'):
            errors.append("Color must be in hex format (e.g., #FF0000)")
        elif len(color) != 7:
            errors.append("Color must be 7 characters (e.g., #FF0000)")

        try:
            int(color[1:], 16)  # Validate hex
        except ValueError:
            errors.append("Invalid color format")

        # Validate shortcut
        if shortcut and len(shortcut) > 20:
            errors.append("Shortcut cannot exceed 20 characters")

        # Validate description
        if len(description) > 200:
            errors.append("Description cannot exceed 200 characters")

        return errors

    def suggest_shortcut(self, event_name: str) -> str:
        """Suggest a shortcut for an event based on its name."""
        name_lower = event_name.lower()

        # Common shortcuts based on first letter
        suggestions = {
            'goal': 'G',
            'shot': 'H',
            'missed': 'M',
            'blocked': 'B',
            'zone': 'Z',
            'dump': 'D',
            'turnover': 'T',
            'takeaway': 'A',
            'faceoff': 'F',
            'penalty': 'P',
            'defensive': 'K'
        }

        for keyword, shortcut in suggestions.items():
            if keyword in name_lower:
                # Check if shortcut is available
                if not self._check_hotkey_conflict("", shortcut):
                    return shortcut

        # Fallback: use first letter of name
        first_letter = event_name[0].upper()
        if not self._check_hotkey_conflict("", first_letter):
            return first_letter

        return ""

    def _validate_event(self, event: CustomEventType) -> Optional[str]:
        """Validate event object."""
        errors = self.validate_event_data(
            event.name, event.color, event.shortcut, event.description
        )
        return "; ".join(errors) if errors else None

    def _check_hotkey_conflict(self, exclude_event: str, shortcut: str) -> Optional[str]:
        """Check if shortcut conflicts with existing events."""
        for event in self.get_all_events():
            if event.name != exclude_event and event.shortcut == shortcut:
                return event.name
        return None

    def create_event_from_dict(self, data: Dict[str, Any]) -> Optional[CustomEventType]:
        """Create event from dictionary data."""
        try:
            return CustomEventType(
                name=data.get('name', ''),
                color=data.get('color', '#CCCCCC'),
                shortcut=data.get('shortcut', ''),
                description=data.get('description', '')
            )
        except Exception as e:
            print(f"Error creating event from dict: {e}")
            return None

    def event_to_dict(self, event: CustomEventType) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'name': event.name,
            'color': event.color,
            'shortcut': event.shortcut,
            'description': event.description
        }

    def get_available_colors(self) -> List[str]:
        """Get list of suggested colors for events."""
        return [
            '#FF0000',  # Red
            '#00FF00',  # Green
            '#0000FF',  # Blue
            '#FFFF00',  # Yellow
            '#FF00FF',  # Magenta
            '#00FFFF',  # Cyan
            '#FFA500',  # Orange
            '#800080',  # Purple
            '#FFC0CB',  # Pink
            '#A52A2A',  # Brown
            '#808080',  # Gray
            '#000000',  # Black
        ]

    def cleanup(self):
        """Cleanup resources."""
        # Disconnect signals if needed
        pass
