from __future__ import annotations

from typing import Optional

from models.domain.project import Project
from services.serialization import ProjectIO


class ProjectController:
    """Контроллер управления проектами (без UI)."""

    def __init__(self, project_io: ProjectIO):
        self.project_io = project_io
        self.current_project: Optional[Project] = None

    def new_project(self, name: str = "Untitled") -> Project:
        self.current_project = Project(name=name)
        self.current_project.is_modified = False
        self.current_project.file_path = ""
        return self.current_project

    def save_project(self, filepath: str) -> bool:
        if not self.current_project:
            return False

        try:
            success = self.project_io.save_project(self.current_project, filepath)
        except Exception as e:
            print(f"Save project failed: {e}")
            return False

        if success:
            self.current_project.file_path = filepath
            self.current_project.is_modified = False
        return success

    def load_project(self, filepath: str) -> Optional[Project]:
        try:
            project = self.project_io.load_project(filepath)
        except Exception as e:
            print(f"Load project failed: {e}")
            return None

        if not project:
            return None

        self.current_project = project
        self.current_project.file_path = filepath
        self.current_project.is_modified = False
        return self.current_project

    def save_project_auto(self, parent_widget=None) -> bool:
        """Сохранить проект автоматически.

        Если файл уже задан — сохраняет туда.
        Если нет — показывает диалог выбора файла.

        Args:
            parent_widget: родительский виджет для диалога (QWidget или None).

        Returns:
            True если сохранение прошло успешно, False если отменено или ошибка.
        """
        if not self.current_project:
            return False

        # Если путь уже есть — сохраняем без диалога
        if self.current_project.file_path:
            return self.save_project(self.current_project.file_path)

        # Нет пути — показываем диалог
        try:
            from PySide6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                parent_widget,
                "Сохранить проект",
                "project.hep",
                "Файлы проекта (*.hep);;Все файлы (*)"
            )
            if not file_path:
                return False  # Пользователь отменил

            if not file_path.endswith(".hep"):
                file_path += ".hep"

            return self.save_project(file_path)

        except Exception as e:
            print(f"Ошибка авто-сохранения: {e}")
            return False

    def has_unsaved_changes(self) -> bool:
        return bool(self.current_project and self.current_project.is_modified)

    def mark_as_modified(self) -> None:
        if self.current_project:
            self.current_project.is_modified = True