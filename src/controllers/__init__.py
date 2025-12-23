"""Controllers - связующее звено между Views и Services."""

from .playback_controller import PlaybackController
from .timeline_controller import TimelineController
from .project_controller import ProjectController
from .main_controller import MainController

__all__ = [
    'PlaybackController',
    'TimelineController',
    'ProjectController',
    'MainController'
]
