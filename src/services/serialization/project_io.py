import json
import os
from typing import Optional

# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.project import Project
except ImportError:
    # Для случаев, когда запускаем из src/
    from ...models.domain.project import Project


class ProjectIO:
    """Сервис для сохранения и загрузки проектов."""

    @staticmethod
    def save_project(project: Project, filepath: str) -> bool:
        """Сохранить проект в JSON файл."""
        try:
            # Создать директорию если не существует
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # Конвертировать проект в словарь и сохранить
            project_data = project.to_dict()
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    @staticmethod
    def load_project(filepath: str) -> Optional[Project]:
        """Загрузить проект из JSON файла."""
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Project file not found: {filepath}")

            # Загрузить данные из файла
            with open(filepath, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # Создать проект из данных
            project = Project.from_dict(project_data)
            return project

        except Exception as e:
            print(f"Error loading project: {e}")
            return None
