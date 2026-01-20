# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.project import Project
    from services.serialization import ProjectIO
    from PySide6.QtWidgets import QFileDialog, QMessageBox
except ImportError:
    # Для случаев, когда запускаем из src/
    from ..models.domain.project import Project
    from ..services.serialization import ProjectIO
    from PySide6.QtWidgets import QFileDialog, QMessageBox


class ProjectController:
    """Контроллер управления проектами."""

    def __init__(self, project_io: ProjectIO):
        self.project_io = project_io
        self.current_project: Project = None

    def new_project(self, name: str = "Untitled") -> Project:
        """Создать новый проект."""
        self.current_project = Project(name=name)
        return self.current_project

    def save_project(self, filepath: str) -> bool:
        """Сохранить проект."""
        if not self.current_project:
            return False

        success = self.project_io.save_project(self.current_project, filepath)
        if success:
            # После успешного сохранения сбрасываем флаг изменений
            self.current_project.file_path = filepath
            self.current_project.is_modified = False

        return success

    def load_project(self, filepath: str) -> Project:
        """Загрузить проект."""
        project = self.project_io.load_project(filepath)
        if project:
            self.current_project = project
            self.current_project.file_path = filepath
            self.current_project.is_modified = False  # Новый загруженный проект не имеет изменений
        return project

    def get_current_project(self) -> Project:
        """Получить текущий проект."""
        return self.current_project

    def has_unsaved_changes(self) -> bool:
        """Проверить, есть ли несохраненные изменения в текущем проекте."""
        return self.current_project and self.current_project.is_modified

    def mark_as_modified(self):
        """Пометить текущий проект как измененный."""
        if self.current_project:
            self.current_project.is_modified = True

    def save_project_auto(self, parent_window=None) -> bool:
        """Умное сохранение проекта.

        Если проект уже имеет файл - сохраняет в него.
        Если файл новый - предлагает выбрать место сохранения.

        Returns:
            bool: True если сохранение успешно
        """
        if not self.current_project:
            return False

        # Если проект уже имеет файл, сохраняем в него
        if self.current_project.file_path:
            return self.save_project(self.current_project.file_path)
        else:
            # Проект новый, предлагаем выбрать файл
            return self.save_project_as(parent_window)

    def save_project_as(self, parent_window=None) -> bool:
        """Сохранить проект под новым именем."""
        if not self.current_project:
            return False

        # Диалог выбора файла
        file_path, _ = QFileDialog.getSaveFileName(
            parent_window,
            "Сохранить проект",
            f"{self.current_project.name}.hep",
            "Project Files (*.hep);;All Files (*)"
        )

        if file_path:
            # Убедимся, что расширение .hep
            if not file_path.endswith('.hep'):
                file_path += '.hep'

            return self.save_project(file_path)
        else:
            return False  # Пользователь отменил
