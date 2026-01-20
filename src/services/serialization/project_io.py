import json
import zipfile
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.project import Project
except ImportError:
    # Для случаев, когда запускаем из src/
    from ...models.domain.project import Project


class ProjectIO:
    """Сервис для сохранения и загрузки проектов в формате .hep (ZIP архивы)."""

    HEP_VERSION = "1.0"
    MANIFEST_FILE = "project.json"

    @staticmethod
    def save_project(project: Project, filepath: str) -> bool:
        """Сохранить проект в .hep файл (ZIP архив)."""
        try:
            file_path = Path(filepath)

            # Убедиться, что путь имеет расширение .hep
            if file_path.suffix.lower() != ".hep":
                file_path = file_path.with_suffix(".hep")

            # Создать директорию если не существует
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Обновить время модификации
            project.modified_at = datetime.now().isoformat()

            # Создать ZIP архив
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as hep:
                # Написать project.json
                manifest = {
                    "version": ProjectIO.HEP_VERSION,
                    "project": project.to_dict()
                }

                hep.writestr(ProjectIO.MANIFEST_FILE,
                           json.dumps(manifest, indent=2, ensure_ascii=False))

            return True
        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    @staticmethod
    def load_project(filepath: str) -> Optional[Project]:
        """Загрузить проект из .hep файла (ZIP архив)."""
        try:
            file_path = Path(filepath)

            if not file_path.exists():
                raise FileNotFoundError(f"Project file not found: {filepath}")

            # Открыть ZIP архив
            with zipfile.ZipFile(file_path, 'r') as hep:
                # Прочитать project.json
                manifest_data = hep.read(ProjectIO.MANIFEST_FILE)
                manifest = json.loads(manifest_data)

                # Проверить версию
                version = manifest.get("version", "1.0")
                if version != ProjectIO.HEP_VERSION:
                    print(f"Warning: Project version {version} may not be compatible")

                # Загрузить проект
                project_data = manifest.get("project", {})
                project = Project.from_dict(project_data)

                return project

        except Exception as e:
            print(f"Error loading project: {e}")
            return None
