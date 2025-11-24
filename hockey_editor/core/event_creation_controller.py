"""Event creation controller с горячими клавишами."""

from enum import Enum
from dataclasses import dataclass
from typing import Callable, Optional
from PySide6.QtCore import QTimer, Signal, QObject

from models.marker import Marker, EventType


class EventCreationMode(Enum):
    MANUAL = "manual"
    FIXED_DURATION = "fixed_duration"


class RecordingState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    RECORDED = "recorded"


@dataclass
class EventCreationConfig:
    mode: EventCreationMode = EventCreationMode.MANUAL
    fixed_duration_ms: int = 5000
    pre_roll_ms: int = 3000
    post_roll_ms: int = 0
    click_sound_enabled: bool = True


class EventCreationController(QObject):
    """Управляет созданием событий через горячие клавиши."""

    recording_started = Signal(object, int)
    recording_updated = Signal(object, int)
    recording_finished = Signal(object)
    state_changed = Signal(object)

    def __init__(self, config: Optional[EventCreationConfig] = None):
        super().__init__()
        self.config = config or EventCreationConfig()
        self.state = RecordingState.IDLE
        self.current_event_type: Optional[EventType] = None
        self.recording_start_frame: Optional[int] = None
        self.recording_start_frame_with_preroll: Optional[int] = None
        
        self.get_current_frame: Optional[Callable[[], int]] = None
        self.get_frame_rate: Optional[Callable[[], float]] = None
        self.set_seek_frame: Optional[Callable[[int], None]] = None

    def set_video_controller(self, get_current_frame: Callable[[], int],
                             get_frame_rate: Callable[[], float],
                             set_seek_frame: Callable[[int], None]):
        self.get_current_frame = get_current_frame
        self.get_frame_rate = get_frame_rate
        self.set_seek_frame = set_seek_frame

    def on_hotkey_pressed(self, event_type: EventType) -> bool:
        if self.state == RecordingState.IDLE:
            self._start_recording(event_type)
            return True
        elif self.state == RecordingState.RECORDING and self.current_event_type == event_type:
            self._finish_recording()
            return True
        return False

    def _start_recording(self, event_type: EventType):
        current_frame = self.get_current_frame() if self.get_current_frame else 0
        self.current_event_type = event_type
        self.recording_start_frame = current_frame
        
        frame_rate = self.get_frame_rate() if self.get_frame_rate else 30.0
        pre_roll_frames = int(self.config.pre_roll_ms / 1000.0 * frame_rate)
        self.recording_start_frame_with_preroll = max(0, current_frame - pre_roll_frames)
        
        self.state = RecordingState.RECORDING
        self.state_changed.emit(self.state)
        self.recording_started.emit(event_type, current_frame)

    def _finish_recording(self):
        if not self.get_current_frame or not self.current_event_type:
            return

        current_frame = self.get_current_frame()
        frame_rate = self.get_frame_rate() if self.get_frame_rate else 30.0
        
        post_roll_frames = int(self.config.post_roll_ms / 1000.0 * frame_rate)
        end_frame = current_frame + post_roll_frames
        
        marker = Marker(
            start_frame=self.recording_start_frame_with_preroll,
            end_frame=end_frame,
            type=self.current_event_type,
            note=""
        )
        
        if self.set_seek_frame and self.recording_start_frame_with_preroll is not None:
            self.set_seek_frame(self.recording_start_frame_with_preroll)
        
        self.state = RecordingState.RECORDED
        self.state_changed.emit(self.state)
        self.recording_finished.emit(marker)
        
        QTimer.singleShot(500, lambda: self._reset_state())

    def _reset_state(self):
        self.state = RecordingState.IDLE
        self.current_event_type = None
        self.recording_start_frame = None
        self.recording_start_frame_with_preroll = None
        self.state_changed.emit(self.state)

    def update_recording_frame(self, current_frame: int):
        if self.state == RecordingState.RECORDING:
            self.recording_updated.emit(self.current_event_type, current_frame)

    def cancel_recording(self):
        if self.state == RecordingState.RECORDING:
            self._reset_state()
