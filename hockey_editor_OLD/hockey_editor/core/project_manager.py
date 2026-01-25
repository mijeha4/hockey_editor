"""
Project Manager - система сохранения/загрузки проектов (.hep файлы).
"""

import json
import zipfile
import os
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from ..models.marker import Marker, EventType


class Project:
    """Модель проекта Hockey Editor Pro."""
    
    def __init__(self, name: str, video_path: str = "", fps: float = 30.0):
        self.name = name
        self.video_path = video_path
        self.fps = fps
        self.markers: List[Marker] = []
        self.created_at = datetime.now().isoformat()
        self.modified_at = datetime.now().isoformat()
        self.version = "1.0"
    
    def to_dict(self) -> Dict:
        """Конвертировать проект в словарь."""
        return {
            "name": self.name,
            "video_path": self.video_path,
            "fps": self.fps,
            "version": self.version,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "markers": [
                {
                    "event_name": marker.event_name,
                    "start_frame": marker.start_frame,
                    "end_frame": marker.end_frame,
                    "note": marker.note or ""
                }
                for marker in self.markers
            ]
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Project':
        """Создать проект из словаря."""
        project = cls(data["name"], data.get("video_path", ""), data.get("fps", 30.0))
        project.created_at = data.get("created_at", project.created_at)
        project.modified_at = data.get("modified_at", project.modified_at)
        project.version = data.get("version", "1.0")
        
        # Загрузить маркеры
        for marker_data in data.get("markers", []):
            marker = Marker(
                event_name=marker_data["event_name"],
                start_frame=marker_data["start_frame"],
                end_frame=marker_data["end_frame"],
                note=marker_data.get("note", "")
            )
            project.markers.append(marker)
        
        return project


class ProjectManager:
    """Управление проектами (.hep файлы = ZIP с project.json)."""
    
    HEP_VERSION = "1.0"
    MANIFEST_FILE = "project.json"
    
    @staticmethod
    def create_project(name: str, video_path: str = "", fps: float = 30.0) -> Project:
        """Создать новый проект."""
        return Project(name, video_path, fps)
    
    @staticmethod
    def save_project(project: Project, file_path: str) -> bool:
        """Сохранить проект в .hep файл."""
        try:
            file_path = Path(file_path)
            
            # Убедиться, что путь имеет расширение .hep
            if file_path.suffix.lower() != ".hep":
                file_path = file_path.with_suffix(".hep")
            
            # Обновить время модификации
            project.modified_at = datetime.now().isoformat()
            
            # Создать ZIP архив
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as hep:
                # Написать project.json
                manifest = {
                    "version": ProjectManager.HEP_VERSION,
                    "project": project.to_dict()
                }
                
                hep.writestr(ProjectManager.MANIFEST_FILE, 
                           json.dumps(manifest, indent=2, ensure_ascii=False))
            
            return True
        except Exception as e:
            print(f"Error saving project: {e}")
            return False
    
    @staticmethod
    def load_project(file_path: str) -> Optional[Project]:
        """Загрузить проект из .hep файла."""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                print(f"Project file not found: {file_path}")
                return None
            
            # Открыть ZIP архив
            with zipfile.ZipFile(file_path, 'r') as hep:
                # Прочитать project.json
                manifest_data = hep.read(ProjectManager.MANIFEST_FILE)
                manifest = json.loads(manifest_data)
                
                # Проверить версию
                version = manifest.get("version", "1.0")
                if version != ProjectManager.HEP_VERSION:
                    print(f"Warning: Project version {version} may not be compatible")
                
                # Загрузить проект
                project_data = manifest.get("project", {})
                project = Project.from_dict(project_data)
                
                return project
        except Exception as e:
            print(f"Error loading project: {e}")
            return None
    
    @staticmethod
    def get_recent_projects(max_count: int = 5) -> List[str]:
        """Получить список недавних проектов из конфига."""
        from ..utils.settings_manager import get_settings_manager
        settings = get_settings_manager()
        recent = settings.load_recent_projects()
        return recent[:max_count]
    
    @staticmethod
    def add_to_recent(file_path: str):
        """Добавить проект в список недавних."""
        from ..utils.settings_manager import get_settings_manager
        settings = get_settings_manager()
        
        recent = settings.load_recent_projects()
        file_path = str(Path(file_path).absolute())
        
        # Удалить если уже есть
        if file_path in recent:
            recent.remove(file_path)
        
        # Добавить в начало
        recent.insert(0, file_path)
        
        # Сохранить (макс 10 проектов)
        settings.save_recent_projects(recent[:10])
