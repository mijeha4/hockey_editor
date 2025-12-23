# Используем абсолютные импорты для совместимости с run_test.py
try:
    from models.domain.project import Project
    from services.serialization import ProjectIO
except ImportError:
    # Для случаев, когда запускаем из src/
    from ..models.domain.project import Project
    from ..services.serialization import ProjectIO


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

        return self.project_io.save_project(self.current_project, filepath)

    def load_project(self, filepath: str) -> Project:
        """Загрузить проект."""
        project = self.project_io.load_project(filepath)
        if project:
            self.current_project = project
        return project

    def get_current_project(self) -> Project:
        """Получить текущий проект."""
        return self.current_project
