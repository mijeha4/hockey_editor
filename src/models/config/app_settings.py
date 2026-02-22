from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any
from enum import Enum


class Theme(Enum):
    DARK = "dark"
    LIGHT = "light"


class RecordingMode(Enum):
    DYNAMIC = "dynamic"
    FIXED_LENGTH = "fixed_length"


@dataclass
class EventType:
    name: str
    color: str
    shortcut: str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "color": self.color,
            "shortcut": self.shortcut,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventType":
        return cls(
            name=str(data.get("name", "")).strip(),
            color=str(data.get("color", "#CCCCCC")).strip(),
            shortcut=str(data.get("shortcut", "")).strip(),
            description=str(data.get("description", "")).strip(),
        )


@dataclass
class AppSettings:
    """Application settings model."""

    default_events: List[EventType] = field(default_factory=lambda: [
        EventType(name="Goal", color="#FF0000", shortcut="G", description="Goal scored"),
        EventType(name="Shot on Goal", color="#FF5722", shortcut="H", description="Shot on goal"),
        EventType(name="Missed Shot", color="#FF9800", shortcut="M", description="Shot missed the net"),
        EventType(name="Blocked Shot", color="#795548", shortcut="B", description="Shot blocked"),

        EventType(name="Zone Entry", color="#2196F3", shortcut="Z", description="Entry into offensive zone"),
        EventType(name="Zone Exit", color="#03A9F4", shortcut="X", description="Exit from defensive zone"),
        EventType(name="Dump In", color="#00BCD4", shortcut="D", description="Dump puck into zone"),

        EventType(name="Turnover", color="#607D8B", shortcut="T", description="Loss of puck possession"),
        EventType(name="Takeaway", color="#4CAF50", shortcut="A", description="Puck possession gained"),
        EventType(name="Faceoff Win", color="#8BC34A", shortcut="F", description="Faceoff won"),
        EventType(name="Faceoff Loss", color="#558B2F", shortcut="L", description="Faceoff lost"),

        EventType(name="Defensive Block", color="#3F51B5", shortcut="K", description="Shot blocked in defense"),
        EventType(name="Penalty", color="#9C27B0", shortcut="P", description="Penalty called"),
    ])

    hotkeys: Dict[str, str] = field(default_factory=lambda: {
        "ATTACK": "A", "DEFENSE": "D", "SHIFT": "S"
    })

    recording_mode: str = RecordingMode.FIXED_LENGTH.value
    fixed_duration_sec: int = 10
    pre_roll_sec: float = 3.0
    post_roll_sec: float = 0.0

    track_colors: Dict[str, str] = field(default_factory=lambda: {
        "ATTACK": "#8b0000",
        "DEFENSE": "#000080",
        "SHIFT": "#006400",
    })

    window_x: int = 0
    window_y: int = 0
    window_width: int = 1800
    window_height: int = 1000

    autosave_enabled: bool = True
    autosave_interval_minutes: int = 5

    recent_projects: List[str] = field(default_factory=list)

    custom_events: List[Dict] = field(default_factory=list)

    language: str = "ru"
    playback_speed: float = 1.0
    theme: str = Theme.DARK.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            # include default_events so it can be customized if needed
            "default_events": [e.to_dict() for e in self.default_events],

            "hotkeys": dict(self.hotkeys),
            "recording_mode": self.recording_mode,
            "fixed_duration_sec": int(self.fixed_duration_sec),
            "pre_roll_sec": float(self.pre_roll_sec),
            "post_roll_sec": float(self.post_roll_sec),

            "track_colors": dict(self.track_colors),

            "window_x": int(self.window_x),
            "window_y": int(self.window_y),
            "window_width": int(self.window_width),
            "window_height": int(self.window_height),

            "autosave_enabled": bool(self.autosave_enabled),
            "autosave_interval_minutes": int(self.autosave_interval_minutes),

            "recent_projects": list(self.recent_projects),

            "custom_events": list(self.custom_events),

            "language": self.language,
            "playback_speed": float(self.playback_speed),
            "theme": self.theme,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppSettings":
        default = cls()

        # recording_mode validation
        rec = str(data.get("recording_mode", default.recording_mode))
        if rec not in (RecordingMode.DYNAMIC.value, RecordingMode.FIXED_LENGTH.value):
            rec = default.recording_mode

        theme = str(data.get("theme", default.theme))
        if theme not in (Theme.DARK.value, Theme.LIGHT.value):
            theme = default.theme

        # default_events (optional key)
        default_events_data = data.get("default_events")
        if isinstance(default_events_data, list):
            default_events = [EventType.from_dict(x) for x in default_events_data]
            # if bad config produces empty list, fallback
            if not default_events:
                default_events = default.default_events
        else:
            default_events = default.default_events

        return cls(
            default_events=default_events,

            hotkeys=dict(data.get("hotkeys", default.hotkeys)),
            recording_mode=rec,
            fixed_duration_sec=int(data.get("fixed_duration_sec", default.fixed_duration_sec)),
            pre_roll_sec=float(data.get("pre_roll_sec", default.pre_roll_sec)),
            post_roll_sec=float(data.get("post_roll_sec", default.post_roll_sec)),

            track_colors=dict(data.get("track_colors", default.track_colors)),

            window_x=int(data.get("window_x", default.window_x)),
            window_y=int(data.get("window_y", default.window_y)),
            window_width=int(data.get("window_width", default.window_width)),
            window_height=int(data.get("window_height", default.window_height)),

            autosave_enabled=bool(data.get("autosave_enabled", default.autosave_enabled)),
            autosave_interval_minutes=int(data.get("autosave_interval_minutes", default.autosave_interval_minutes)),

            recent_projects=list(data.get("recent_projects", default.recent_projects)),

            custom_events=list(data.get("custom_events", default.custom_events)),

            language=str(data.get("language", default.language)),
            playback_speed=float(data.get("playback_speed", default.playback_speed)),
            theme=theme,
        )