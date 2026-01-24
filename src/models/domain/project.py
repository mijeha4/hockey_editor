from datetime import datetime
from typing import List, Dict, Any
from PySide6.QtCore import QObject, Signal
from .marker import Marker


class Project(QObject):
    """Модель проекта Hockey Editor с реактивностью PySide6."""

    # Сигналы
    marker_added = Signal(int, Marker)  # index, marker
    marker_removed = Signal(int)  # index
    marker_changed = Signal(int, Marker)  # index, marker
    markers_cleared = Signal()

    def __init__(self, name: str, video_path: str = "", fps: float = 30.0):
        super().__init__()
        self._name = name
        self._video_path = video_path
        self._fps = fps
        self._markers: List[Marker] = []
        self._created_at = datetime.now().isoformat()
        self._modified_at = datetime.now().isoformat()
        self._version = "1.0"
        self._file_path = ""
        self._is_modified = False

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value

    @property
    def video_path(self) -> str:
        return self._video_path

    @video_path.setter
    def video_path(self, value: str):
        self._video_path = value

    @property
    def fps(self) -> float:
        return self._fps

    @fps.setter
    def fps(self, value: float):
        self._fps = value

    @property
    def markers(self) -> List[Marker]:
        return self._markers

    @property
    def created_at(self) -> str:
        return self._created_at

    @created_at.setter
    def created_at(self, value: str):
        self._created_at = value

    @property
    def modified_at(self) -> str:
        return self._modified_at

    @modified_at.setter
    def modified_at(self, value: str):
        self._modified_at = value

    @property
    def version(self) -> str:
        return self._version

    @version.setter
    def version(self, value: str):
        self._version = value

    @property
    def file_path(self) -> str:
        return self._file_path

    @file_path.setter
    def file_path(self, value: str):
        self._file_path = value

    @property
    def is_modified(self) -> bool:
        return self._is_modified

    @is_modified.setter
    def is_modified(self, value: bool):
        self._is_modified = value

    def add_marker(self, marker: Marker, index: int = -1):
        """Добавить маркер в проект."""
        if index == -1:
            index = len(self._markers)
        self._markers.insert(index, marker)
        # Подключаемся к сигналам маркера
        marker.changed.connect(lambda: self._on_marker_changed(marker))
        self.marker_added.emit(index, marker)
        self._is_modified = True

    def remove_marker(self, index: int):
        """Удалить маркер из проекта."""
        if 0 <= index < len(self._markers):
            marker = self._markers.pop(index)
            # Отключаемся от сигналов маркера
            marker.changed.disconnect()
            self.marker_removed.emit(index)
            self._is_modified = True

    def clear_markers(self):
        """Очистить все маркеры."""
        for marker in self._markers:
            marker.changed.disconnect()
        self._markers.clear()
        self.markers_cleared.emit()
        self._is_modified = True

    def _on_marker_changed(self, marker: Marker):
        """Обработчик изменения маркера."""
        try:
            index = self._markers.index(marker)
            self.marker_changed.emit(index, marker)
            self._is_modified = True
        except ValueError:
            # Маркер не найден в списке
            pass

    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать проект в словарь."""
        return {
            "name": self._name,
            "video_path": self._video_path,
            "fps": self._fps,
            "version": self._version,
            "created_at": self._created_at,
            "modified_at": self._modified_at,
            "markers": [marker.to_dict() for marker in self._markers]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Создать проект из словаря."""
        project = cls(
            name=data["name"],
            video_path=data.get("video_path", ""),
            fps=data.get("fps", 30.0)
        )
        project._created_at = data.get("created_at", project._created_at)
        project._modified_at = data.get("modified_at", project._modified_at)
        project._version = data.get("version", "1.0")

        # Загрузить маркеры
        for marker_data in data.get("markers", []):
            marker = Marker.from_dict(marker_data)
            project.add_marker(marker)

        return project
