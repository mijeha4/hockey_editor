# custom_events.py
# Backward compatibility imports for custom events functionality

from .custom_events import (
    CustomEventType,
    CustomEventManager,
    get_custom_event_manager,
    reset_custom_event_manager
)

# Re-export all classes and functions for backward compatibility
__all__ = [
    'CustomEventType',
    'CustomEventManager',
    'get_custom_event_manager',
    'reset_custom_event_manager'
]
