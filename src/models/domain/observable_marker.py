"""
Observable Marker - reactive model for timeline segments.

Provides reactive updates when marker properties change,
following strict MVC architecture principles.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from PySide6.QtCore import QObject, Signal

from .marker import Marker


class ObservableMarker(QObject):
    """Reactive marker model that emits signals on property changes."""
    
    # Сигналы изменений свойств
    start_frame_changed = Signal(int)
    end_frame_changed = Signal(int)
    event_name_changed = Signal(str)
    note_changed = Signal(str)
    
    # Сигнал общего изменения маркера
    marker_changed = Signal()
    
    def __init__(self, start_frame: int, end_frame: int, event_name: str, note: str = ""):
        super().__init__()
        
        # Используем приватные поля для хранения значений
        self._start_frame = start_frame
        self._end_frame = end_frame
        self._event_name = event_name
        self._note = note
    
    @property
    def start_frame(self) -> int:
        """Get start frame."""
        return self._start_frame
    
    @start_frame.setter
    def start_frame(self, value: int) -> None:
        """Set start frame with validation and signal emission."""
        if value != self._start_frame:
            self._start_frame = value
            self.start_frame_changed.emit(value)
            self.marker_changed.emit()
    
    @property
    def end_frame(self) -> int:
        """Get end frame."""
        return self._end_frame
    
    @end_frame.setter
    def end_frame(self, value: int) -> None:
        """Set end frame with validation and signal emission."""
        if value != self._end_frame:
            self._end_frame = value
            self.end_frame_changed.emit(value)
            self.marker_changed.emit()
    
    @property
    def event_name(self) -> str:
        """Get event name."""
        return self._event_name
    
    @event_name.setter
    def event_name(self, value: str) -> None:
        """Set event name with signal emission."""
        if value != self._event_name:
            self._event_name = value
            self.event_name_changed.emit(value)
            self.marker_changed.emit()
    
    @property
    def note(self) -> str:
        """Get note."""
        return self._note
    
    @note.setter
    def note(self, value: str) -> None:
        """Set note with signal emission."""
        if value != self._note:
            self._note = value
            self.note_changed.emit(value)
            self.marker_changed.emit()
    
    def set_range(self, start_frame: int, end_frame: int) -> None:
        """Set both start and end frames efficiently."""
        if start_frame != self._start_frame:
            self._start_frame = start_frame
            self.start_frame_changed.emit(start_frame)
        
        if end_frame != self._end_frame:
            self._end_frame = end_frame
            self.end_frame_changed.emit(end_frame)
        
        # Emit general change signal only once
        self.marker_changed.emit()
    
    def to_marker(self) -> Marker:
        """Convert to regular Marker for compatibility."""
        return Marker(
            start_frame=self._start_frame,
            end_frame=self._end_frame,
            event_name=self._event_name,
            note=self._note
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "start_frame": self._start_frame,
            "end_frame": self._end_frame,
            "event_name": self._event_name,
            "note": self._note
        }
    
    @classmethod
    def from_marker(cls, marker: Marker) -> 'ObservableMarker':
        """Create ObservableMarker from regular Marker."""
        return cls(
            start_frame=marker.start_frame,
            end_frame=marker.end_frame,
            event_name=marker.event_name,
            note=marker.note
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ObservableMarker':
        """Create ObservableMarker from dictionary."""
        return cls(
            start_frame=data["start_frame"],
            end_frame=data["end_frame"],
            event_name=data.get("event_name", "Attack"),
            note=data.get("note", "")
        )


class ObservableMarkerList(QObject):
    """Reactive list of markers that emits signals on changes."""
    
    # Сигналы изменений списка
    markers_changed = Signal()  # Общее изменение списка
    marker_added = Signal(ObservableMarker)  # Добавлен маркер
    marker_removed = Signal(ObservableMarker)  # Удален маркер
    marker_modified = Signal(ObservableMarker)  # Изменен маркер
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._markers: List[ObservableMarker] = []
    
    def __len__(self) -> int:
        """Get number of markers."""
        return len(self._markers)
    
    def __getitem__(self, index: int) -> ObservableMarker:
        """Get marker by index."""
        return self._markers[index]
    
    def __iter__(self):
        """Iterate over markers."""
        return iter(self._markers)
    
    def append(self, marker: ObservableMarker) -> None:
        """Add marker to list."""
        self._markers.append(marker)
        self.marker_added.emit(marker)
        self.markers_changed.emit()
        
        # Подключаем сигналы изменений маркера к сигналам списка
        marker.marker_changed.connect(lambda: self.marker_modified.emit(marker))
    
    def remove(self, marker: ObservableMarker) -> None:
        """Remove marker from list."""
        if marker in self._markers:
            self._markers.remove(marker)
            self.marker_removed.emit(marker)
            self.markers_changed.emit()
    
    def insert(self, index: int, marker: ObservableMarker) -> None:
        """Insert marker at index."""
        self._markers.insert(index, marker)
        self.marker_added.emit(marker)
        self.markers_changed.emit()
        
        # Подключаем сигналы изменений маркера
        marker.marker_changed.connect(lambda: self.marker_modified.emit(marker))
    
    def clear(self) -> None:
        """Clear all markers."""
        # Отключаем сигналы от всех маркеров
        for marker in self._markers:
            try:
                marker.marker_changed.disconnect()
            except TypeError:
                pass  # Сигнал не был подключен
        
        self._markers.clear()
        self.markers_changed.emit()
    
    def to_list(self) -> List[Marker]:
        """Convert to list of regular Markers for compatibility."""
        return [marker.to_marker() for marker in self._markers]
    
    def from_list(self, markers: List[Marker]) -> None:
        """Initialize from list of regular Markers."""
        self.clear()
        for marker in markers:
            observable_marker = ObservableMarker.from_marker(marker)
            self.append(observable_marker)
    
    def get_index(self, marker: ObservableMarker) -> int:
        """Get index of marker in list."""
        return self._markers.index(marker)