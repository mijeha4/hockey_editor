"""
Widgets - UI компоненты для отображения данных.

Содержит виджеты для отображения и взаимодействия с данными.
"""

from .player_controls import PlayerControls
from .segment_list import SegmentListWidget
from .timeline import TimelineWidget
from .event_card_delegate import EventCardDelegate
from .event_shortcut_list_widget import EventShortcutListWidget
from .drawing_overlay import DrawingOverlay, DrawingTool

__all__ = ['PlayerControls', 'SegmentListWidget', 'TimelineWidget', 'EventCardDelegate', 'EventShortcutListWidget', 'DrawingOverlay', 'DrawingTool']
