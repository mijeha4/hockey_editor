"""
Filter Controller - manages filtering of video segments.

Handles event type filtering, notes filtering, and provides interface
for filter management and application.
"""

from typing import Set, List, Optional
from PySide6.QtCore import QObject, Signal

# Импорты для работы из корня проекта (main.py добавляет src в sys.path)
from models.domain.marker import Marker
from services.events.custom_event_manager import get_custom_event_manager


class FilterController(QObject):
    """Controller for managing segment filters."""

    # Signals
    filters_changed = Signal()  # Emitted when filters are changed

    def __init__(self) -> None:
        super().__init__()

        self.event_manager = get_custom_event_manager()

        # Filter state
        self.filter_event_types: Set[str] = set()  # Selected event type names
        self.filter_has_notes: bool = False        # Filter by segments with notes
        self.selected_marker_ids: Set[int] = set() # Selected marker IDs for filtering

        # Connect to event manager changes
        self.event_manager.events_changed.connect(self._on_events_changed)

    def _on_events_changed(self) -> None:
        """Handle event manager changes - update filters if needed."""
        # If filtered event types are no longer available, clear them
        available_events = {event.name for event in self.event_manager.get_all_events()}
        self.filter_event_types = self.filter_event_types.intersection(available_events)

        if len(self.filter_event_types) != len(self.filter_event_types.intersection(available_events)):
            self.filters_changed.emit()

    def set_event_type_filter(self, event_types: Set[str]) -> None:
        """Set the event type filter.

        Args:
            event_types: Set of event type names to filter by (empty for all)
        """
        if self.filter_event_types != event_types:
            self.filter_event_types = event_types.copy()
            self.filters_changed.emit()

    def add_event_type_filter(self, event_type: str) -> None:
        """Add an event type to the filter.

        Args:
            event_type: Event type name to add
        """
        if event_type not in self.filter_event_types:
            self.filter_event_types.add(event_type)
            self.filters_changed.emit()

    def remove_event_type_filter(self, event_type: str) -> None:
        """Remove an event type from the filter.

        Args:
            event_type: Event type name to remove
        """
        if event_type in self.filter_event_types:
            self.filter_event_types.remove(event_type)
            self.filters_changed.emit()

    def clear_event_type_filter(self) -> None:
        """Clear all event type filters (show all event types)."""
        if self.filter_event_types:
            self.filter_event_types.clear()
            self.filters_changed.emit()

    def set_notes_filter(self, has_notes: bool) -> None:
        """Set the notes filter.

        Args:
            has_notes: True to show only segments with notes, False for all
        """
        if self.filter_has_notes != has_notes:
            self.filter_has_notes = has_notes
            self.filters_changed.emit()

    def toggle_notes_filter(self) -> None:
        """Toggle the notes filter."""
        self.set_notes_filter(not self.filter_has_notes)

    def reset_all_filters(self) -> None:
        """Reset all filters to default state (show all)."""
        changed = False
        if self.filter_event_types:
            self.filter_event_types.clear()
            changed = True
        if self.filter_has_notes:
            self.filter_has_notes = False
            changed = True
        if self.selected_marker_ids:
            self.selected_marker_ids.clear()
            changed = True

        if changed:
            self.filters_changed.emit()

    def set_selected_markers_filter(self, marker_ids: Set[int]) -> None:
        """Set the selected markers filter.

        Args:
            marker_ids: Set of marker IDs to show (empty for all)
        """
        if self.selected_marker_ids != marker_ids:
            self.selected_marker_ids = marker_ids.copy()
            self.filters_changed.emit()

    def add_selected_marker(self, marker_id: int) -> None:
        """Add a marker to the selected markers filter.

        Args:
            marker_id: Marker ID to add
        """
        if marker_id not in self.selected_marker_ids:
            self.selected_marker_ids.add(marker_id)
            self.filters_changed.emit()

    def remove_selected_marker(self, marker_id: int) -> None:
        """Remove a marker from the selected markers filter.

        Args:
            marker_id: Marker ID to remove
        """
        if marker_id in self.selected_marker_ids:
            self.selected_marker_ids.remove(marker_id)
            self.filters_changed.emit()

    def clear_selected_markers(self) -> None:
        """Clear the selected markers filter (show all markers)."""
        if self.selected_marker_ids:
            self.selected_marker_ids.clear()
            self.filters_changed.emit()

    def toggle_selected_marker(self, marker_id: int) -> None:
        """Toggle a marker in the selected markers filter.

        Args:
            marker_id: Marker ID to toggle
        """
        if marker_id in self.selected_marker_ids:
            self.remove_selected_marker(marker_id)
        else:
            self.add_selected_marker(marker_id)

    def is_selected_marker_filtered(self) -> bool:
        """Check if selected markers filter is active.

        Returns:
            True if selected markers filter is active
        """
        return bool(self.selected_marker_ids)

    def get_selected_marker_ids(self) -> Set[int]:
        """Get currently selected marker IDs.

        Returns:
            Set of selected marker IDs
        """
        return self.selected_marker_ids.copy()

    def clear_selected_markers_filter(self) -> None:
        """Clear the selected markers filter and emit signal."""
        if self.selected_marker_ids:
            self.selected_marker_ids.clear()
            self.filters_changed.emit()

    def set_selected_markers_filter_active(self, active: bool) -> None:
        """Set the selected markers filter to active or inactive state.

        Args:
            active: True to activate filter, False to deactivate
        """
        if active and not self.selected_marker_ids:
            # If trying to activate but no markers selected, do nothing
            return
        elif not active and self.selected_marker_ids:
            # If deactivating, clear the selection
            self.clear_selected_markers_filter()

    def get_filter_mode(self) -> str:
        """Get current filter mode.

        Returns:
            'selected' if selected markers filter is active,
            'all' if no filters are active,
            'filtered' if other filters are active
        """
        if self.selected_marker_ids:
            return 'selected'
        elif self.filter_event_types or self.filter_has_notes:
            return 'filtered'
        else:
            return 'all'

    def toggle_selected_markers_mode(self) -> None:
        """Toggle between showing all markers and only selected markers."""
        if self.selected_marker_ids:
            # If selected markers are active, deactivate them
            self.clear_selected_markers_filter()
        else:
            # If no selected markers, activate selection mode
            # This will be handled by the UI when markers are selected
            pass

    def is_selected_markers_mode_active(self) -> bool:
        """Check if selected markers mode is active.

        Returns:
            True if only selected markers should be shown
        """
        return bool(self.selected_marker_ids)

    def get_selected_markers_count(self) -> int:
        """Get the number of selected markers.

        Returns:
            Number of selected markers
        """
        return len(self.selected_marker_ids)

    def clear_all_filters(self) -> None:
        """Clear all filters including selected markers."""
        self.clear_event_type_filter()
        self.set_notes_filter(False)
        self.clear_selected_markers_filter()

    def passes_filters(self, marker: Marker) -> bool:
        """Check if a marker passes current filters.

        Args:
            marker: Marker to check

        Returns:
            True if marker passes all filters
        """
        # Selected markers filter (highest priority)
        if self.selected_marker_ids and marker.id not in self.selected_marker_ids:
            return False

        # Event type filter
        if self.filter_event_types and marker.event_name not in self.filter_event_types:
            return False

        # Notes filter
        if self.filter_has_notes and not marker.note.strip():
            return False

        return True

    def filter_markers(self, markers: List[Marker]) -> List[Marker]:
        """Filter a list of markers according to current filters.

        Args:
            markers: List of markers to filter

        Returns:
            Filtered list of markers
        """
        return [marker for marker in markers if self.passes_filters(marker)]

    def get_available_event_types(self) -> List[str]:
        """Get list of available event types for filtering.

        Returns:
            List of event type names
        """
        return [event.name for event in self.event_manager.get_all_events()]

    def get_available_event_types_with_display_names(self) -> List[tuple[str, str]]:
        """Get list of available event types with display names.

        Returns:
            List of tuples (event_name, display_name)
        """
        return [(event.name, event.get_localized_name())
                for event in self.event_manager.get_all_events()]

    def get_filtered_event_types(self) -> Set[str]:
        """Get currently filtered event types.

        Returns:
            Set of filtered event type names
        """
        return self.filter_event_types.copy()

    def is_event_type_filtered(self, event_type: str) -> bool:
        """Check if an event type is currently being filtered.

        Args:
            event_type: Event type name to check

        Returns:
            True if event type is in filter
        """
        return event_type in self.filter_event_types

    def is_notes_filtered(self) -> bool:
        """Check if notes filter is active.

        Returns:
            True if notes filter is active
        """
        return self.filter_has_notes

    def has_active_filters(self) -> bool:
        """Check if any filters are currently active.

        Returns:
            True if any filters are active
        """
        return bool(self.filter_event_types) or self.filter_has_notes

    def get_filter_summary(self) -> str:
        """Get a summary of current filters.

        Returns:
            Human-readable filter summary
        """
        parts = []

        if self.filter_event_types:
            event_names = []
            for event_name in self.filter_event_types:
                event = self.event_manager.get_event(event_name)
                if event:
                    event_names.append(event.get_localized_name())
            if event_names:
                parts.append(f"Типы: {', '.join(event_names)}")

        if self.filter_has_notes:
            parts.append("Только с заметками")

        if not parts:
            return "Все сегменты"

        return " | ".join(parts)
