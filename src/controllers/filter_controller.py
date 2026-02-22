"""
Filter Controller - manages segment filtering.

Single source of truth for all filter state.
No other component should store filter state independently.

NOTE: selected_marker_ids was removed from filtering logic.
Table row selection is UI state, not a data filter. Mixing them
caused a feedback loop where clicking a row filtered out all others.
"""

import logging
from typing import List, Set, Tuple

from PySide6.QtCore import QObject, Signal

from models.domain.marker import Marker
from services.events.custom_event_manager import get_custom_event_manager

logger = logging.getLogger(__name__)


class FilterController(QObject):
    """Controller for managing segment filters."""

    filters_changed = Signal()

    def __init__(self) -> None:
        super().__init__()

        self._event_manager = get_custom_event_manager()

        # Private filter state (only real data filters)
        self._filter_event_types: Set[str] = set()
        self._filter_has_notes: bool = False

        self._event_manager.events_changed.connect(self._on_events_changed)

    # ─── Properties ───

    @property
    def event_manager(self):
        """Access to event manager (for combo population, etc.)."""
        return self._event_manager

    @property
    def filter_event_types(self) -> Set[str]:
        """Currently filtered event types (empty = show all)."""
        return self._filter_event_types.copy()

    @property
    def filter_has_notes(self) -> bool:
        """Whether notes filter is active."""
        return self._filter_has_notes

    @property
    def has_active_filters(self) -> bool:
        """Whether any filter is currently active."""
        return bool(
            self._filter_event_types
            or self._filter_has_notes
        )

    # ─── Setters ───

    def set_event_type_filter(self, event_types: Set[str]) -> None:
        """Set event type filter.

        Args:
            event_types: Event type names to show. Empty = show all.
        """
        if self._filter_event_types != event_types:
            self._filter_event_types = event_types.copy()
            self.filters_changed.emit()

    def set_notes_filter(self, has_notes: bool) -> None:
        """Set notes presence filter.

        Args:
            has_notes: If True, only show markers with non-empty notes.
        """
        if self._filter_has_notes != has_notes:
            self._filter_has_notes = has_notes
            self.filters_changed.emit()

    def set_selected_marker_ids(self, marker_ids: Set[int]) -> None:
        """Accept selected marker IDs from UI (for informational purposes).

        NOTE: This no longer affects filtering. Table row selection
        is UI state and must not drive data filtering to avoid
        feedback loops.
        """
        # No-op: kept for API compatibility so callers don't crash.
        # If other components need to know about selection, use
        # SegmentListWidget.selection_changed signal directly.
        pass

    def reset_all_filters(self) -> None:
        """Reset all filters to default (show everything)."""
        if not self.has_active_filters:
            return

        self._filter_event_types.clear()
        self._filter_has_notes = False
        self.filters_changed.emit()
        logger.debug("All filters reset")

    # ─── Filtering logic ───

    def passes_filters(self, marker: Marker) -> bool:
        """Check if a marker passes all current filters.

        Args:
            marker: Marker to check.

        Returns:
            True if marker passes all active filters.
        """
        # Event type filter
        if self._filter_event_types and marker.event_name not in self._filter_event_types:
            return False

        # Notes filter
        if self._filter_has_notes and not (marker.note or "").strip():
            return False

        return True

    def filter_markers(self, markers: List[Marker]) -> List[Tuple[int, Marker]]:
        """Filter markers, preserving original indices.

        Args:
            markers: Full list of markers (unfiltered).

        Returns:
            List of (original_index, marker) for markers that pass filters.
        """
        return [
            (idx, marker)
            for idx, marker in enumerate(markers)
            if self.passes_filters(marker)
        ]

    # ─── Internal handlers ───

    def _on_events_changed(self) -> None:
        """Handle changes in event definitions.

        Removes filter entries for event types that no longer exist.
        """
        available_events = {
            event.name for event in self._event_manager.get_all_events()
        }
        invalid_types = self._filter_event_types - available_events

        if invalid_types:
            logger.info(
                "Removing invalid filter event types: %s", invalid_types
            )
            self._filter_event_types -= invalid_types
            self.filters_changed.emit()

    # ─── Cleanup ───

    def cleanup(self) -> None:
        """Disconnect signals and release resources."""
        try:
            self._event_manager.events_changed.disconnect(
                self._on_events_changed
            )
        except (RuntimeError, TypeError):
            pass