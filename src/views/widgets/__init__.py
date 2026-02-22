"""
Widgets - UI компоненты для отображения данных.

Ленивые импорты для предотвращения циклических зависимостей.
"""

__all__ = [
    'PlayerControls', 'SegmentListWidget', 'TimelineWidget',
    'EventCardDelegate', 'EventShortcutListWidget',
    'DrawingOverlay', 'DrawingTool', 'ScalableVideoLabel',
]


def __getattr__(name: str):
    if name == 'PlayerControls':
        from .player_controls import PlayerControls
        return PlayerControls
    if name == 'SegmentListWidget':
        from .segment_list import SegmentListWidget
        return SegmentListWidget
    if name == 'TimelineWidget':
        from .timeline import TimelineWidget
        return TimelineWidget
    if name == 'EventCardDelegate':
        from .event_card_delegate import EventCardDelegate
        return EventCardDelegate
    if name == 'EventShortcutListWidget':
        from .event_shortcut_list_widget import EventShortcutListWidget
        return EventShortcutListWidget
    if name in ('DrawingOverlay', 'DrawingTool'):
        from .drawing_overlay import DrawingOverlay, DrawingTool
        if name == 'DrawingOverlay':
            return DrawingOverlay
        return DrawingTool
    if name == 'ScalableVideoLabel':
        from .scalable_video_label import ScalableVideoLabel
        return ScalableVideoLabel
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")