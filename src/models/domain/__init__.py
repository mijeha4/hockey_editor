"""Domain models - чистые модели данных без зависимостей от UI."""

from .marker import Marker
from .project import Project
from .event_type import EventType

__all__ = ['Marker', 'Project', 'EventType']
