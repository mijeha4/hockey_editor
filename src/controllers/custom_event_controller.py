"""
Custom Event Controller - manages custom event types.

Handles CRUD operations for custom event types, including validation,
import/export, and synchronization with the event manager service.
"""

import logging
from typing import List, Optional, Dict, Any
from PySide6.QtCore import QObject, Signal

from services.events.custom_event_manager import get_custom_event_manager, CustomEventManager
from services.events.custom_event_type import CustomEventType

logger = logging.getLogger(__name__)


class CustomEventController(QObject):
    """Controller for managing custom event types.

    This controller owns all validation logic.
    The event_manager handles persistence and storage.
    events_changed is proxied from event_manager — never emitted manually here.
    """

    # Сигналы
    events_changed = Signal()
    event_added = Signal(CustomEventType)
    event_updated = Signal(str, CustomEventType)
    event_deleted = Signal(str)
    events_reset = Signal()
    validation_error = Signal(str, str)

    # Константы валидации
    MAX_NAME_LENGTH = 50
    MAX_SHORTCUT_LENGTH = 20
    MAX_DESCRIPTION_LENGTH = 200
    COLOR_LENGTH = 7  # #RRGGBB

    def __init__(self, parent=None):
        super().__init__(parent)

        self._event_manager: CustomEventManager = get_custom_event_manager()

        # Проксируем сигнал менеджера — единственный источник events_changed.
        # Менеджер эмитит events_changed при любом изменении данных
        # (add, update, delete, import, reset). Контроллер НЕ дублирует этот emit.
        self._event_manager.events_changed.connect(self.events_changed)

    # ─── Properties ───

    @property
    def event_manager(self) -> CustomEventManager:
        """Access to event manager (read-only operations)."""
        return self._event_manager

    # ─── Read operations ───

    def get_all_events(self) -> List[CustomEventType]:
        """Get all event types.

        Returns:
            List of all registered event types.
        """
        return self._event_manager.get_all_events()

    def get_event(self, name: str) -> Optional[CustomEventType]:
        """Get event by name.

        Args:
            name: Event name to look up.

        Returns:
            CustomEventType if found, None otherwise.
        """
        return self._event_manager.get_event(name)

    def is_default_event(self, name: str) -> bool:
        """Check if event is a default (non-deletable) event.

        Args:
            name: Event name to check.

        Returns:
            True if event is a default event.
        """
        return self._event_manager.is_default_event(name)

    def get_default_events(self) -> List[CustomEventType]:
        """Get list of default event types.

        Returns:
            List of default event types.
        """
        return self._event_manager.get_default_events()

    # ─── CRUD operations ───

    def add_event(self, event: CustomEventType) -> bool:
        """Add new event type.

        Validates the event, checks for name and shortcut conflicts,
        then delegates to event_manager.

        Args:
            event: Event to add.

        Returns:
            True if event was added successfully.
        """
        # Validate
        error = self._validate_event(event)
        if error:
            self.validation_error.emit("general", error)
            return False

        # Check name conflict
        if self._event_manager.get_event(event.name):
            self.validation_error.emit(
                "name", f"Событие '{event.name}' уже существует"
            )
            return False

        # Check shortcut conflict
        if event.shortcut:
            conflict = self._find_shortcut_conflict(event.name, event.shortcut)
            if conflict:
                self.validation_error.emit(
                    "shortcut",
                    f"Сочетание '{event.shortcut}' уже используется для '{conflict}'"
                )
                return False

        # Add via manager (manager emits events_changed)
        success = self._event_manager.add_event(event)
        if success:
            self.event_added.emit(event)

        return success

    def update_event(self, old_name: str, new_event: CustomEventType) -> bool:
        """Update existing event type.

        Args:
            old_name: Current name of the event to update.
            new_event: New event data.

        Returns:
            True if event was updated successfully.
        """
        # Validate
        error = self._validate_event(new_event)
        if error:
            self.validation_error.emit("general", error)
            return False

        # Check that original event exists
        if not self._event_manager.get_event(old_name):
            self.validation_error.emit(
                "general", f"Событие '{old_name}' не найдено"
            )
            return False

        # Check name conflict (only if name changed)
        if old_name != new_event.name:
            if self._event_manager.get_event(new_event.name):
                self.validation_error.emit(
                    "name", f"Событие '{new_event.name}' уже существует"
                )
                return False

        # Check shortcut conflict
        if new_event.shortcut:
            conflict = self._find_shortcut_conflict(
                new_event.name, new_event.shortcut
            )
            if conflict:
                self.validation_error.emit(
                    "shortcut",
                    f"Сочетание '{new_event.shortcut}' уже используется для '{conflict}'"
                )
                return False

        # Update via manager (manager emits events_changed)
        success = self._event_manager.update_event(old_name, new_event)
        if success:
            self.event_updated.emit(old_name, new_event)

        return success

    def delete_event(self, name: str) -> bool:
        """Delete event type.

        Default events cannot be deleted.

        Args:
            name: Name of event to delete.

        Returns:
            True if event was deleted successfully.
        """
        # Check existence
        if not self._event_manager.get_event(name):
            self.validation_error.emit(
                "general", f"Событие '{name}' не найдено"
            )
            return False

        # Protect default events
        if self._event_manager.is_default_event(name):
            self.validation_error.emit(
                "general",
                f"Невозможно удалить стандартное событие '{name}'"
            )
            return False

        # Delete via manager (manager emits events_changed)
        success = self._event_manager.delete_event(name)
        if success:
            self.event_deleted.emit(name)

        return success

    def reset_to_defaults(self) -> None:
        """Reset events to application defaults.

        Removes all custom events, restores default events.
        Manager emits events_changed internally.
        """
        self._event_manager.reset_to_defaults()
        self.events_reset.emit()

    # ─── Import / Export ───

    def export_events(self, file_path: str) -> bool:
        """Export events to file.

        Args:
            file_path: Path to export file.

        Returns:
            True if export succeeded.
        """
        try:
            return self._event_manager.export_events(file_path)
        except Exception as e:
            logger.error("Export failed: %s", e)
            self.validation_error.emit("export", f"Ошибка экспорта: {e}")
            return False

    def import_events(self, file_path: str) -> bool:
        """Import events from file.

        Manager emits events_changed internally on success.
        No manual emit needed here.

        Args:
            file_path: Path to import file.

        Returns:
            True if import succeeded.
        """
        try:
            return self._event_manager.import_events(file_path)
        except Exception as e:
            logger.error("Import failed: %s", e)
            self.validation_error.emit("import", f"Ошибка импорта: {e}")
            return False

    # ─── Validation ───

    def validate_event_data(
        self,
        name: str,
        color: str,
        shortcut: str = "",
        description: str = "",
    ) -> List[str]:
        """Validate raw event data fields.

        Args:
            name: Event name.
            color: Color in #RRGGBB format.
            shortcut: Keyboard shortcut.
            description: Event description.

        Returns:
            List of error messages. Empty list means valid.
        """
        errors = []

        # Name validation
        stripped_name = name.strip()
        if not stripped_name:
            errors.append("Название события не может быть пустым")
        elif len(stripped_name) > self.MAX_NAME_LENGTH:
            errors.append(
                f"Название не может превышать {self.MAX_NAME_LENGTH} символов"
            )

        # Color validation
        color_error = self._validate_color(color)
        if color_error:
            errors.append(color_error)

        # Shortcut validation
        if shortcut and len(shortcut) > self.MAX_SHORTCUT_LENGTH:
            errors.append(
                f"Сочетание клавиш не может превышать "
                f"{self.MAX_SHORTCUT_LENGTH} символов"
            )

        # Description validation
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            errors.append(
                f"Описание не может превышать "
                f"{self.MAX_DESCRIPTION_LENGTH} символов"
            )

        return errors

    # ─── Statistics ───

    def get_event_stats(self) -> Dict[str, int]:
        """Get statistics about registered events.

        Returns:
            Dictionary with event counts.
        """
        events = self.get_all_events()
        default_count = sum(
            1 for e in events if self._event_manager.is_default_event(e.name)
        )

        return {
            "total_events": len(events),
            "default_events": default_count,
            "custom_events": len(events) - default_count,
            "events_with_shortcuts": sum(1 for e in events if e.shortcut),
            "events_with_descriptions": sum(1 for e in events if e.description),
        }

    # ─── Serialization helpers ───

    def create_event_from_dict(self, data: Dict[str, Any]) -> Optional[CustomEventType]:
        """Create event from dictionary data.

        Args:
            data: Dictionary with event fields.

        Returns:
            CustomEventType if valid, None otherwise.
        """
        try:
            event = CustomEventType(
                name=data.get("name", ""),
                color=data.get("color", "#CCCCCC"),
                shortcut=data.get("shortcut", ""),
                description=data.get("description", ""),
            )
            # Validate before returning
            error = self._validate_event(event)
            if error:
                logger.warning("Invalid event data from dict: %s", error)
                return None
            return event
        except (TypeError, ValueError) as e:
            logger.warning("Error creating event from dict: %s", e)
            return None

    @staticmethod
    def event_to_dict(event: CustomEventType) -> Dict[str, str]:
        """Convert event to dictionary.

        Args:
            event: Event to convert.

        Returns:
            Dictionary representation of the event.
        """
        return {
            "name": event.name,
            "color": event.color,
            "shortcut": event.shortcut,
            "description": event.description,
        }

    # ─── Shortcut suggestions ───

    def suggest_shortcut(self, event_name: str) -> str:
        """Suggest an available shortcut for an event based on its name.

        Tries common keyword mappings first, then falls back to first letter.

        Args:
            event_name: Name of the event.

        Returns:
            Suggested shortcut string, or empty string if none available.
        """
        if not event_name:
            return ""

        name_lower = event_name.lower()

        # Keyword → shortcut mappings
        keyword_shortcuts = {
            "goal": "G",
            "shot": "S",
            "missed": "M",
            "blocked": "B",
            "zone": "Z",
            "dump": "D",
            "turnover": "T",
            "takeaway": "A",
            "faceoff": "F",
            "penalty": "P",
            "defensive": "K",
        }

        for keyword, shortcut in keyword_shortcuts.items():
            if keyword in name_lower:
                if not self._find_shortcut_conflict("", shortcut):
                    return shortcut

        # Fallback: first available letter from the name
        for char in event_name:
            if char.isalpha():
                upper_char = char.upper()
                if not self._find_shortcut_conflict("", upper_char):
                    return upper_char

        return ""

    # ─── Color palette ───

    @staticmethod
    def get_available_colors() -> List[str]:
        """Get list of suggested colors for events.

        Returns:
            List of hex color strings.
        """
        return [
            "#FF0000",  # Red
            "#00FF00",  # Green
            "#0000FF",  # Blue
            "#FFFF00",  # Yellow
            "#FF00FF",  # Magenta
            "#00FFFF",  # Cyan
            "#FFA500",  # Orange
            "#800080",  # Purple
            "#FFC0CB",  # Pink
            "#A52A2A",  # Brown
            "#808080",  # Gray
            "#000000",  # Black
        ]

    # ─── Private helpers ───

    def _validate_event(self, event: CustomEventType) -> Optional[str]:
        """Validate a CustomEventType object.

        Args:
            event: Event to validate.

        Returns:
            Error message string if invalid, None if valid.
        """
        errors = self.validate_event_data(
            event.name, event.color, event.shortcut, event.description
        )
        return "; ".join(errors) if errors else None

    @staticmethod
    def _validate_color(color: str) -> Optional[str]:
        """Validate a hex color string.

        Args:
            color: Color string to validate.

        Returns:
            Error message if invalid, None if valid.
        """
        if not color or len(color) != 7 or color[0] != "#":
            return "Цвет должен быть в формате #RRGGBB"
        try:
            int(color[1:], 16)
        except ValueError:
            return "Цвет содержит недопустимые символы"
        return None

    def _find_shortcut_conflict(
        self, exclude_event_name: str, shortcut: str
    ) -> Optional[str]:
        """Find an existing event that uses the given shortcut.

        Args:
            exclude_event_name: Event name to exclude from check
                (useful when updating an event).
            shortcut: Shortcut to check.

        Returns:
            Name of conflicting event, or None if no conflict.
        """
        for event in self.get_all_events():
            if event.name != exclude_event_name and event.shortcut == shortcut:
                return event.name
        return None

    # ─── Cleanup ───

    def cleanup(self) -> None:
        """Disconnect signals and release resources."""
        try:
            self._event_manager.events_changed.disconnect(self.events_changed)
        except (RuntimeError, TypeError):
            pass