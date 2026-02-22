from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtCore import QObject, Signal

from .marker import Marker


class Project(QObject):
    """Project model with Qt reactivity (signals)."""

    # Signals
    marker_added = Signal(int, Marker)     # index, marker
    marker_removed = Signal(int)           # index
    markers_cleared = Signal()
    markers_replaced = Signal()            # bulk update (optional)
    modified_changed = Signal(bool)        # dirty flag changed (optional)

    def __init__(self, name: str, video_path: str = "", fps: float = 30.0):
        super().__init__()
        self._name = name
        self._video_path = video_path
        self._fps = fps

        self._markers: List[Marker] = []

        now = datetime.now().isoformat()
        self._created_at = now
        self._modified_at = now
        self._version = "1.0"

        self._file_path = ""
        self._is_modified = False

    # ──────────────────────────────────────────────────────────────────────
    # Properties
    # ──────────────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if self._name != value:
            self._name = value
            self._touch_modified()

    @property
    def video_path(self) -> str:
        return self._video_path

    @video_path.setter
    def video_path(self, value: str) -> None:
        if self._video_path != value:
            self._video_path = value
            self._touch_modified()

    @property
    def fps(self) -> float:
        return self._fps

    @fps.setter
    def fps(self, value: float) -> None:
        if self._fps != value:
            self._fps = value
            self._touch_modified()

    @property
    def markers(self) -> List[Marker]:
        """Return a copy to prevent external mutation without signals."""
        return list(self._markers)

    def marker_at(self, index: int) -> Optional[Marker]:
        if 0 <= index < len(self._markers):
            return self._markers[index]
        return None

    @property
    def created_at(self) -> str:
        return self._created_at

    @created_at.setter
    def created_at(self, value: str) -> None:
        self._created_at = value

    @property
    def modified_at(self) -> str:
        return self._modified_at

    @property
    def version(self) -> str:
        return self._version

    @version.setter
    def version(self, value: str) -> None:
        self._version = value

    @property
    def file_path(self) -> str:
        return self._file_path

    @file_path.setter
    def file_path(self, value: str) -> None:
        self._file_path = value

    @property
    def is_modified(self) -> bool:
        return self._is_modified

    @is_modified.setter
    def is_modified(self, value: bool) -> None:
        if self._is_modified != value:
            self._is_modified = value
            self.modified_changed.emit(value)

    # ──────────────────────────────────────────────────────────────────────
    # Marker operations
    # ──────────────────────────────────────────────────────────────────────

    def add_marker(self, marker: Marker, index: int = -1, *, emit_signal: bool = True, mark_modified: bool = True) -> None:
        """Add marker to project."""
        if index == -1 or index > len(self._markers):
            index = len(self._markers)
        if index < 0:
            index = 0

        self._markers.insert(index, marker)

        if mark_modified:
            self._touch_modified()

        if emit_signal:
            self.marker_added.emit(index, marker)

    def remove_marker(self, index: int, *, emit_signal: bool = True, mark_modified: bool = True) -> None:
        """Remove marker by index."""
        if 0 <= index < len(self._markers):
            self._markers.pop(index)

            if mark_modified:
                self._touch_modified()

            if emit_signal:
                self.marker_removed.emit(index)

    def clear_markers(self, *, emit_signal: bool = True, mark_modified: bool = True) -> None:
        """Clear markers."""
        if not self._markers:
            return

        self._markers.clear()

        if mark_modified:
            self._touch_modified()

        if emit_signal:
            self.markers_cleared.emit()

    def set_markers(self, markers: List[Marker], *, emit_signal: bool = True, mark_modified: bool = True) -> None:
        """Replace all markers at once."""
        self._markers = list(markers)

        if mark_modified:
            self._touch_modified()

        if emit_signal:
            self.markers_replaced.emit()

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    def _touch_modified(self) -> None:
        self._modified_at = datetime.now().isoformat()
        self.is_modified = True  # uses setter + signal

    # ──────────────────────────────────────────────────────────────────────
    # Serialization
    # ──────────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "video_path": self._video_path,
            "fps": self._fps,
            "version": self._version,
            "created_at": self._created_at,
            "modified_at": self._modified_at,
            "markers": [m.to_dict() for m in self._markers],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        project = cls(
            name=data.get("name", "Untitled"),
            video_path=data.get("video_path", ""),
            fps=data.get("fps", 30.0),
        )

        project._created_at = data.get("created_at", project._created_at)
        project._modified_at = data.get("modified_at", project._modified_at)
        project._version = data.get("version", project._version)

        markers = [Marker.from_dict(m) for m in data.get("markers", [])]
        # Load without signals and without marking modified
        project.set_markers(markers, emit_signal=False, mark_modified=False)

        # Loaded project should not be dirty
        project.is_modified = False

        return project