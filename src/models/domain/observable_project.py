"""
Observable Project - reactive project model.

Provides reactive updates when project markers change,
following strict MVC architecture principles.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from PySide6.QtCore import QObject, Signal

from .marker import Marker
from .observable_marker import ObservableMarker, ObservableMarkerList


class ObservableProject(QObject):
    """Reactive project model that emits signals on marker changes."""
    
    # Сигналы изменений проекта
    markers_changed = Signal()  # Общее изменение списка маркеров
    marker_added = Signal(ObservableMarker)  # Добавлен маркер
    marker_removed = Signal(ObservableMarker)  # Удален маркер
    marker_modified = Signal(ObservableMarker)  # Изменен маркер
    project_modified = Signal()  # Проект изменен
    
    def __init__(self, name: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self.name = name
        self.video_path = ""
        self.fps = 30.0
        self.created_at = datetime.now().isoformat()
        self.modified_at = datetime.now().isoformat()
        self.version = "1.0"
        
        # Поля для отслеживания изменений
        self.file_path = ""
        self.is_modified = False
        
        # Реактивный список маркеров
        self.markers = ObservableMarkerList(self)
        
        # Подключаем сигналы списка маркеров к сигналам проекта
        self._connect_marker_signals()
    
    def _connect_marker_signals(self) -> None:
        """Connect marker list signals to project signals."""
        self.markers.markers_changed.connect(self._on_markers_changed)
        self.markers.marker_added.connect(self.marker_added)
        self.markers.marker_removed.connect(self.marker_removed)
        self.markers.marker_modified.connect(self.marker_modified)
    
    def _on_markers_changed(self) -> None:
        """Handle markers list changes."""
        self.markers_changed.emit()
        self._mark_modified()
    
    def _mark_modified(self) -> None:
        """Mark project as modified."""
        self.is_modified = True
        self.modified_at = datetime.now().isoformat()
        self.project_modified.emit()
    
    def add_marker(self, marker: ObservableMarker) -> None:
        """Add marker to project."""
        self.markers.append(marker)
        self._mark_modified()
    
    def remove_marker(self, marker: ObservableMarker) -> None:
        """Remove marker from project."""
        self.markers.remove(marker)
        self._mark_modified()
    
    def clear_markers(self) -> None:
        """Clear all markers."""
        self.markers.clear()
        self._mark_modified()
    
    def to_project(self) -> 'Project':
        """Convert to regular Project for compatibility."""
        from .project import Project
        
        project = Project(
            name=self.name,
            video_path=self.video_path,
            fps=self.fps
        )
        project.created_at = self.created_at
        project.modified_at = self.modified_at
        project.version = self.version
        project.file_path = self.file_path
        project.is_modified = self.is_modified
        
        # Конвертируем маркеры
        project.markers = self.markers.to_list()
        
        return project
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "video_path": self.video_path,
            "fps": self.fps,
            "version": self.version,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "markers": [marker.to_dict() for marker in self.markers]
        }
    
    @classmethod
    def from_project(cls, project: 'Project') -> 'ObservableProject':
        """Create ObservableProject from regular Project."""
        observable_project = cls(project.name)
        
        observable_project.video_path = project.video_path
        observable_project.fps = project.fps
        observable_project.created_at = project.created_at
        observable_project.modified_at = project.modified_at
        observable_project.version = project.version
        observable_project.file_path = project.file_path
        observable_project.is_modified = project.is_modified
        
        # Конвертируем маркеры
        observable_project.markers.from_list(project.markers)
        
        return observable_project
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ObservableProject':
        """Create ObservableProject from dictionary."""
        project = cls(data["name"])
        
        project.video_path = data.get("video_path", "")
        project.fps = data.get("fps", 30.0)
        project.created_at = data.get("created_at", project.created_at)
        project.modified_at = data.get("modified_at", project.modified_at)
        project.version = data.get("version", "1.0")
        
        # Загрузить маркеры
        markers_data = data.get("markers", [])
        for marker_data in markers_data:
            marker = ObservableMarker.from_dict(marker_data)
            project.markers.append(marker)
        
        return project
    
    def get_marker_index(self, marker: ObservableMarker) -> int:
        """Get index of marker in project."""
        return self.markers.get_index(marker)