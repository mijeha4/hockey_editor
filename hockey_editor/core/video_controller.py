from PySide6.QtCore import QObject, Signal, QTimer
from typing import List, Optional, Dict
from enum import Enum
import json
import os
from .video_processor import VideoProcessor
from .event_creation_controller import EventCreationController, RecordingMode
from ..models.marker import Marker, EventType
from ..utils.settings_manager import get_settings_manager
from ..utils.custom_events import get_custom_event_manager


class RecordingMode(Enum):
    """Режимы расстановки отрезков."""
    DYNAMIC = "dynamic"          # Два нажатия = начало и конец
    FIXED_LENGTH = "fixed_length"  # Одно нажатие = отрезок фиксированной длины


class VideoController(QObject):
    """Главный контроллер видео с синхронизацией воспроизведения."""
    
    # Сигналы
    playback_time_changed = Signal(int)  # frame_idx
    markers_changed = Signal()
    recording_status_changed = Signal(str, str)  # event_type (A/D/S), status (Recording/Complete)
    timeline_update = Signal()
    current_frame_update = Signal(int)  # frame_idx
    frame_ready = Signal(object)  # np.ndarray (текущий кадр)

    def __init__(self):
        super().__init__()

        self.processor = VideoProcessor()
        self.markers: List[Marker] = []

        # SettingsManager для персистентности
        self.settings = get_settings_manager()

        # CustomEventManager - менеджер событий
        self.event_manager = get_custom_event_manager()

        # EventCreationController - контроллер создания событий
        self.event_creation_controller = EventCreationController(self)

        # Подключить сигналы EventCreationController
        self.event_creation_controller.recording_status_changed.connect(self.recording_status_changed)
        self.event_creation_controller.markers_changed.connect(self.markers_changed)
        self.event_creation_controller.timeline_update.connect(self.timeline_update)

        # UndoRedoManager
        from ..utils.undo_redo import UndoRedoManager
        self.undo_redo = UndoRedoManager()

        # Параметры воспроизведения
        self.playing = False
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_tick)
        self.frame_time_ms = 33  # ~30 FPS (рассчитывается на основе FPS видео)
        self.playback_speed = 1.0  # Скорость воспроизведения (1.0 = нормальная скорость)

        # Загрузить скорость воспроизведения
        self.playback_speed = self.settings.load_playback_speed()

    def load_video(self, video_path: str) -> bool:
        """Загрузить видеофайл (ПАУЗИРОВАН!)."""
        success = self.processor.load(video_path)
        if success:
            # Рассчитать frame_time_ms на основе FPS видео и скорости воспроизведения
            fps = self.processor.get_fps()
            if fps > 0:
                self.frame_time_ms = int(1000 / (fps * self.playback_speed))

            # Убедиться, что видео на паузе
            self.playing = False
            self.playback_timer.stop()

            # Обновить маркеры и UI
            self.markers = []
            self.markers_changed.emit()
            self.playback_time_changed.emit(0)
            self.current_frame_update.emit(0)
            self.timeline_update.emit()

            # Отправить первый кадр на UI
            frame = self.processor.get_current_frame()
            if frame is not None:
                self.frame_ready.emit(frame)

        return success

    def play(self):
        """Начать воспроизведение."""
        if self.processor.cap is None or self.playing:
            return
        
        self.playing = True
        self.playback_timer.start(self.frame_time_ms)

    def pause(self):
        """Пауза."""
        self.playing = False
        self.playback_timer.stop()

    def toggle_play_pause(self):
        """Переключить Play/Pause."""
        if self.playing:
            self.pause()
        else:
            self.play()

    def stop(self):
        """Остановка и возврат в начало."""
        self.pause()
        self.seek_frame(0)

    def seek_frame(self, frame_idx: int):
        """Перемотать на кадр (НЕ запускает воспроизведение)."""
        if self.processor.cap is None:
            return
        
        self.processor.seek(frame_idx)
        
        # Отправить сигналы об обновлении
        self.playback_time_changed.emit(frame_idx)
        self.current_frame_update.emit(frame_idx)
        self.timeline_update.emit()
        
        # Отправить кадр на UI
        frame = self.processor.get_current_frame()
        if frame is not None:
            self.frame_ready.emit(frame)

    def _on_playback_tick(self):
        """Таймер воспроизведения - вызывается каждый frame_time_ms."""
        if not self.processor.cap or not self.playing:
            return
        
        # Переместиться на следующий кадр
        success = self.processor.advance_frame()
        if not success:
            # Конец видео
            self.pause()
            return
        
        # Получить текущий индекс кадра
        current_frame_idx = self.processor.get_current_frame_idx()
        
        # Эмит сигналов об обновлении
        self.playback_time_changed.emit(current_frame_idx)
        self.current_frame_update.emit(current_frame_idx)
        self.timeline_update.emit()
        
        # Отправить текущий кадр на UI
        frame = self.processor.get_current_frame()
        if frame is not None:
            self.frame_ready.emit(frame)

    def on_hotkey_pressed(self, key: str):
        """Обработка нажатия горячей клавиши - делегировать EventCreationController."""
        self.event_creation_controller.on_hotkey_pressed(key)

    def delete_marker(self, idx: int):
        """Удалить отрезок (с undo/redo)."""
        if 0 <= idx < len(self.markers):
            from ..utils.undo_redo import DeleteMarkerCommand
            command = DeleteMarkerCommand(self.markers, idx)
            self.undo_redo.push_command(command)
            self.markers_changed.emit()
            self.timeline_update.emit()

    def clear_markers(self):
        """Удалить все отрезки (с undo/redo)."""
        from ..utils.undo_redo import ClearMarkersCommand
        command = ClearMarkersCommand(self.markers)
        self.undo_redo.push_command(command)
        self.markers_changed.emit()
        self.timeline_update.emit()

    def cancel_recording(self):
        """Отменить текущую запись - делегировать EventCreationController."""
        self.event_creation_controller.cancel_recording()

    def set_recording_mode(self, mode):
        """Установить режим расстановки отрезков - делегировать EventCreationController."""
        self.event_creation_controller.set_recording_mode(mode)

    def set_fixed_duration(self, seconds: int):
        """Установить фиксированную длину отрезка - делегировать EventCreationController."""
        self.event_creation_controller.set_fixed_duration(seconds)

    def set_pre_roll(self, seconds: float):
        """Установить откат перед началом отрезка - делегировать EventCreationController."""
        self.event_creation_controller.set_pre_roll(seconds)

    def set_post_roll(self, seconds: float):
        """Установить добавление в конец отрезка - делегировать EventCreationController."""
        self.event_creation_controller.set_post_roll(seconds)

    def set_playback_speed(self, speed: float):
        """Установить скорость воспроизведения."""
        if speed <= 0:
            return  # Не допускаем нулевую или отрицательную скорость

        self.playback_speed = speed

        # Обновить frame_time_ms если видео загружено
        fps = self.processor.get_fps()
        if fps > 0:
            self.frame_time_ms = int(1000 / (fps * self.playback_speed))

        # Если воспроизведение активно, перезапустить таймер с новой скоростью
        if self.playing:
            self.playback_timer.start(self.frame_time_ms)

        # Сохранить настройку
        self.settings.save_playback_speed(speed)

    def get_playback_speed(self) -> float:
        """Получить текущую скорость воспроизведения."""
        return self.playback_speed

    @property
    def recording_mode(self):
        """Получить текущий режим записи."""
        return self.event_creation_controller.recording_mode

    @property
    def fixed_duration_sec(self):
        """Получить фиксированную длительность."""
        return self.event_creation_controller.fixed_duration_sec

    @property
    def pre_roll_sec(self):
        """Получить предварительный откат."""
        return self.event_creation_controller.pre_roll_sec

    @property
    def post_roll_sec(self):
        """Получить добавление в конец."""
        return self.event_creation_controller.post_roll_sec

    # Метод update_hotkeys убран - hotkeys теперь управляются через CustomEventManager

    def get_current_frame_idx(self) -> int:
        """Получить текущий индекс кадра."""
        return self.processor.get_current_frame_idx()

    def get_fps(self) -> float:
        """Получить FPS видео."""
        return self.processor.get_fps()

    def get_total_frames(self) -> int:
        """Получить общее количество кадров."""
        return self.processor.get_total_frames()

    def cleanup(self):
        """Очистить ресурсы."""
        self.pause()
        self.processor.cleanup()
        self.markers.clear()

    # ===== ПРОЕКТЫ =====
    
    def save_project(self, file_path: str) -> bool:
        """Сохранить проект в файл."""
        from .project_manager import ProjectManager, Project

        project = Project(
            name=os.path.basename(self.processor.video_path) if self.processor.video_path else "Untitled",
            video_path=self.processor.video_path,
            fps=self.get_fps()
        )
        project.markers = self.markers.copy()
        
        success = ProjectManager.save_project(project, file_path)
        if success:
            ProjectManager.add_to_recent(file_path)
        return success
    
    def load_project(self, file_path: str) -> tuple[bool, bool]:
        """Загрузить проект из файла.
        Returns: (success, video_missing) - успех загрузки, отсутствует ли видео
        """
        from .project_manager import ProjectManager

        project = ProjectManager.load_project(file_path)
        if not project:
            return False, False

        # Проверить наличие видео файла
        if project.video_path and not os.path.exists(project.video_path):
            # Сохранить проект для последующей установки пути к видео
            self._pending_project = project
            self._pending_project_path = file_path
            ProjectManager.add_to_recent(file_path)
            return True, True  # success=True, video_missing=True

        # Загрузить видео
        if project.video_path:
            if not self.load_video(project.video_path):
                return False, False

        # Загрузить маркеры
        self.markers = project.markers.copy()
        self.markers_changed.emit()

        ProjectManager.add_to_recent(file_path)
        return True, False
    
    def set_video_path(self, new_path: str) -> bool:
        """Установить новый путь к видео для загруженного проекта."""
        if hasattr(self, '_pending_project') and self._pending_project:
            self._pending_project.video_path = new_path
            # Завершить загрузку проекта
            return self._finish_project_loading()

        # Если проект уже загружен, перезагрузить видео
        return self.load_video(new_path)

    def _finish_project_loading(self) -> bool:
        """Завершить загрузку проекта после установки пути к видео."""
        if not hasattr(self, '_pending_project'):
            return False

        project = self._pending_project
        project_path = self._pending_project_path

        # Загрузить видео
        if project.video_path and os.path.exists(project.video_path):
            if not self.load_video(project.video_path):
                return False

        # Загрузить маркеры
        self.markers = project.markers.copy()
        self.markers_changed.emit()

        # Очистить pending
        del self._pending_project
        del self._pending_project_path

        return True

    def get_recent_projects(self) -> List[str]:
        """Получить список недавних проектов."""
        from .project_manager import ProjectManager
        return ProjectManager.get_recent_projects()
    
    # ===== UNDO/REDO =====
    
    def undo(self):
        """Отменить последнюю операцию."""
        self.undo_redo.undo()
        self.markers_changed.emit()
    
    def redo(self):
        """Повторить последнюю отменённую операцию."""
        self.undo_redo.redo()
        self.markers_changed.emit()
    
    def can_undo(self) -> bool:
        """Проверить, можно ли отменить."""
        return self.undo_redo.can_undo()
    
    def can_redo(self) -> bool:
        """Проверить, можно ли повторить."""
        return self.undo_redo.can_redo()
