"""
Custom event types manager for user-defined event categories.

Allows users to define their own event types (Attack, Defense, Shift, etc.)
with custom names and colors. Events are stored in QSettings and used
throughout the application for marker categorization.
"""

from .custom_event_type import CustomEventType
from .custom_event_manager import (
    CustomEventManager,
    get_custom_event_manager,
    reset_custom_event_manager
)

__all__ = [
    'CustomEventType',
    'CustomEventManager',
    'get_custom_event_manager',
    'reset_custom_event_manager'
]
