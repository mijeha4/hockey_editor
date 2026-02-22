"""Controllers - связующее звено между Views и Services.

Импорты выполняются лениво, чтобы избежать циклических зависимостей
между controllers и views пакетами.
"""

__all__ = [
    'PlaybackController',
    'TimelineController',
    'ProjectController',
    'MainController',
]


def __getattr__(name: str):
    """Lazy imports to break circular dependency chain."""
    if name == 'PlaybackController':
        from .playback_controller import PlaybackController
        return PlaybackController
    if name == 'TimelineController':
        from .timeline_controller import TimelineController
        return TimelineController
    if name == 'ProjectController':
        from .project_controller import ProjectController
        return ProjectController
    if name == 'MainController':
        from .main_controller import MainController
        return MainController
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")