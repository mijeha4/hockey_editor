from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any
from .marker import Marker


@dataclass
class Project:
    """Модель проекта Hockey Editor."""

    name: str
    video_path: str = ""
    fps: float = 30.0
    markers: List[Marker] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "1.0"

    # Поля для отслеживания изменений
    file_path: str = ""  # Путь к файлу проекта
    is_modified: bool = False  # Флаг несохраненных изменений

    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать проект в словарь."""
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
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Создать проект из словаря."""
        project = cls(
            name=data["name"],
            video_path=data.get("video_path", ""),
            fps=data.get("fps", 30.0)
        )
        project.created_at = data.get("created_at", project.created_at)
        project.modified_at = data.get("modified_at", project.modified_at)
        project.version = data.get("version", "1.0")

        # Загрузить маркеры
        for marker_data in data.get("markers", []):
            marker = Marker.from_dict(marker_data)
            project.markers.append(marker)

        return project
