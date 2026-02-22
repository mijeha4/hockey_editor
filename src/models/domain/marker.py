from __future__ import annotations

from typing import Dict, Any


class Marker:
    """Video segment marker.

    Contract:
        start_frame is inclusive
        end_frame is exclusive

    Segment covers frames: [start_frame, end_frame)
    Duration in frames: end_frame - start_frame
    """

    def __init__(
        self,
        id: int,
        start_frame: int,
        end_frame: int,
        event_name: str,
        note: str = "",
    ):
        self.id = int(id)
        self.start_frame = int(start_frame)
        self.end_frame = int(end_frame)
        self.event_name = str(event_name)
        self.note = "" if note is None else str(note)

    # ──────────────────────────────────────────────────────────────────────
    # Compatibility
    # ──────────────────────────────────────────────────────────────────────

    def to_marker(self) -> "Marker":
        """Legacy compatibility method.

        Kept for backward compatibility; returns self.
        Prefer using Marker directly.
        """
        return self

    # ──────────────────────────────────────────────────────────────────────
    # Derived properties
    # ──────────────────────────────────────────────────────────────────────

    @property
    def duration_frames(self) -> int:
        return max(0, self.end_frame - self.start_frame)

    def validate(self) -> None:
        """Raise ValueError if marker fields are invalid."""
        if self.id <= 0:
            raise ValueError("Marker.id must be positive")
        if self.start_frame < 0:
            raise ValueError("Marker.start_frame must be >= 0")
        if self.end_frame <= self.start_frame:
            raise ValueError("Marker.end_frame must be > start_frame (exclusive end)")
        if not self.event_name.strip():
            raise ValueError("Marker.event_name must be non-empty")

    # ──────────────────────────────────────────────────────────────────────
    # Serialization
    # ──────────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "event_name": self.event_name,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Marker":
        return cls(
            id=data["id"],
            start_frame=data["start_frame"],
            end_frame=data["end_frame"],
            event_name=data["event_name"],
            note=data.get("note", ""),
        )

    # ──────────────────────────────────────────────────────────────────────
    # Misc
    # ──────────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"Marker(id={self.id}, start_frame={self.start_frame}, end_frame={self.end_frame}, "
            f"event_name={self.event_name!r}, note={self.note!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Marker):
            return False
        return (
            self.id == other.id
            and self.start_frame == other.start_frame
            and self.end_frame == other.end_frame
            and self.event_name == other.event_name
            and self.note == other.note
        )